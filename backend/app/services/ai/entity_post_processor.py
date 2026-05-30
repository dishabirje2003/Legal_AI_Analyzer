import re
from typing import Dict, Any, List

def process_entities(raw_entities: List[Dict[str, str]], text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    
    # 1. FILTER NOISE
    generic_words = {"schedule", "lease", "incidental", "agreement", "contract", "parties", "party", "document", "deed"}
    filtered = []
    for ent in raw_entities:
        t = ent['text'].strip()
        t_lower_ent = t.lower()
        
        if t_lower_ent in generic_words:
            continue
            
        if len(t) < 3 and ent['label'] not in ['DATE', 'MONEY']:
            continue
            
        if re.match(r'^[\d\s\.,]+$', t) and ent['label'] not in ['DATE', 'MONEY', 'LAW']:
            continue
            
        filtered.append(ent)
        
    # 2. DEDUPLICATION & MERGING
    prefixes_to_remove = ["lessee ", "lessor ", "mr. ", "mrs. ", "ms. ", "the ", "buyer ", "seller ", "plaintiff ", "defendant "]
    deduped = {}
    for ent in filtered:
        t = ent['text']
        t_clean = t
        for p in prefixes_to_remove:
            if t_clean.lower().startswith(p):
                t_clean = t_clean[len(p):].strip()
        
        key = (t_clean.lower(), ent['label'])
        if key not in deduped:
            deduped[key] = {'text': t_clean, 'label': ent['label'], 'original': ent['text']}
            
    final_entities = list(deduped.values())

    persons = [e for e in final_entities if e['label'] in ['PERSON', 'ORG']]
    dates = [e for e in final_entities if e['label'] == 'DATE']
    moneys = [e for e in final_entities if e['label'] == 'MONEY']
    gpes = [e for e in final_entities if e['label'] == 'GPE']
    laws_spacy = [e for e in final_entities if e['label'] == 'LAW']

    # Custom Regex-based Extraction (Fallback & Augmentation)
    money_regex = r'(?:rs\.?|₹|\$|usd|inr)\s*[\d,]+(?:\.\d{1,2})?(?:\s*(?:lakhs?|crores?|k|m|b))?'
    for match in re.finditer(money_regex, text_lower):
        val = match.group(0).strip()
        if not any(val in m['text'].lower() or m['text'].lower() in val for m in moneys):
            moneys.append({'text': val, 'original': val})

    # Regex fallback for dates
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',                              
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b',  
        r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',                
    ]
    existing_dates_lower = {d['text'].lower() for d in dates}
    for pattern in date_patterns:
        for match in re.finditer(pattern, text_lower):
            val = match.group(0).strip()
            # Prevent numbers from being classified as dates incorrectly
            if re.match(r'^\d+$', val): continue
            
            if val not in existing_dates_lower:
                dates.append({'text': val, 'original': val})
                existing_dates_lower.add(val)

    # NEW ENTITY PATTERNS
    legal_references = [l['text'] for l in laws_spacy]
    case_identifiers = []
    policy_identifiers = []
    judges = []

    # Legal references
    for match in re.finditer(r'(Section\s\d+[A-Za-z]*\s(?:of\s\w+)?|(?:[A-Z][A-Za-z\s]+)\sAct,\s\d{4})', text):
        val = match.group(0).strip()
        if val not in legal_references:
            legal_references.append(val)

    # Case numbers
    for match in re.finditer(r'(Case\sNo\.?|Appeal\sNo\.?)\s?\d+/?\d*', text, re.IGNORECASE):
        val = match.group(0).strip()
        if val not in case_identifiers:
            case_identifiers.append(val)
            
    # Policy numbers
    for match in re.finditer(r'(Policy\sNo\.?|Claim\sID)\s?:?\s?\w+', text, re.IGNORECASE):
        val = match.group(0).strip()
        if val not in policy_identifiers:
            policy_identifiers.append(val)
            
    # Judges
    for match in re.finditer(r'(Justice|Hon\.?ble)\s[A-Z][a-z]+\s[A-Z][a-z]+', text):
        val = match.group(0).strip()
        if val not in judges:
            judges.append(val)

    # Prevent misclassification: remove judges and laws from parties
    filtered_persons = []
    for p in persons:
        pt = p['text'].lower()
        if any(pt in j.lower() for j in judges) or any(pt in l.lower() for l in legal_references):
            continue
        filtered_persons.append(p)
    persons = filtered_persons

    # Fragment merging for Locations
    merged_locations = []
    gpe_texts = [g['text'] for g in gpes]
    skip = set()
    for i, loc1 in enumerate(gpe_texts):
        if i in skip: continue
        for j, loc2 in enumerate(gpe_texts):
            if i != j and j not in skip:
                pattern = re.escape(loc1) + r'[\s,]+' + re.escape(loc2)
                if re.search(pattern, text, re.IGNORECASE):
                    merged_locations.append(f"{loc1}, {loc2}")
                    skip.add(i)
                    skip.add(j)
                    break
        if i not in skip:
            merged_locations.append(loc1)

    # 3. UNIVERSAL ROLE DETECTION
    roles_dict = [
        "Lessor", "Lessee",
        "Buyer", "Seller",
        "Employer", "Employee",
        "Lender", "Borrower",
        "Licensor", "Licensee",
        "Disclosing Party", "Receiving Party",
        "Plaintiff", "Defendant",
        "Insurer", "Insured", "Policyholder"
    ]
    
    def find_nearest_person(target_idx: int) -> str | None:
        if target_idx == -1: return None
        best_person = None
        min_dist = float('inf')
        for p in persons:
            p_text = p['original'].lower()
            p_idx = text_lower.find(p_text)
            if p_idx != -1:
                dist = abs(p_idx - target_idx)
                if dist < min_dist:
                    min_dist = dist
                    best_person = p['text']
        return best_person

    detected_roles = {}
    for role in roles_dict:
        role_lower = role.lower()
        role_idx = text_lower.find(role_lower)
        if role_idx != -1:
            person = find_nearest_person(role_idx)
            if person:
                # If a person already has a role, maybe skip or append? We'll overwrite for simplicity.
                detected_roles[person] = role

    all_parties = set([p['text'] for p in persons])
    formatted_parties = []
    for party in all_parties:
        if party in detected_roles:
            formatted_parties.append(f"{party} ({detected_roles[party]})")
        else:
            formatted_parties.append(party)

    # 4. DATE AND DURATION NORMALIZATION
    durations = []
    other_dates = []
    
    for d in dates:
        dt = d['text']
        dt_lower = dt.lower()
        if "year" in dt_lower or "month" in dt_lower or ("day" in dt_lower and len(dt.split()) <= 3 and "th" not in dt_lower):
            if re.search(r'\d+', dt):
                durations.append(dt)
            else:
                other_dates.append(dt)
        else:
            norm = re.sub(r'(?:st|nd|rd|th)\s+day\s+of\s+', ' ', dt, flags=re.IGNORECASE)
            norm = re.sub(r',', '', norm)
            norm = re.sub(r'\s+', ' ', norm).strip()
            other_dates.append(norm)

    all_dates = list(set(other_dates))
    all_durations = list(set(durations))

    # 5. MONEY NORMALIZATION
    financials = []
    for m in moneys:
        mt = m['text']
        mt_lower = mt.lower()
        
        # Prevent misclassification: do not classify IDs or policies as money
        if "policy" in mt_lower or "case" in mt_lower or "claim" in mt_lower or "id" in mt_lower or "no" in mt_lower:
            continue
            
        clean_val = re.sub(r'(?<=\d)[,\s]+(?=\d)', '', mt)
        
        mt_idx = text.find(m.get('original', mt))
        context = "amount"
        if mt_idx != -1:
            start = max(0, mt_idx - 30)
            end = min(len(text), mt_idx + len(m.get('original', mt)) + 30)
            surrounding = text_lower[start:end]
            if "rent" in surrounding: context = "rent"
            elif "penalty" in surrounding: context = "penalty"
            elif "deposit" in surrounding: context = "deposit"
            elif "premium" in surrounding: context = "premium"
            elif "claim" in surrounding: context = "claim"
            elif "compensation" in surrounding: context = "compensation"
                
        financials.append(f"{clean_val} ({context})")

    # 6. OUTPUT FORMAT
    return {
        "parties": list(set(formatted_parties)),
        "money": list(set(financials)),
        "dates": all_dates,
        "durations": all_durations,
        "locations": list(set(merged_locations)),
        "legal_references": list(set(legal_references)),
        "case_identifiers": list(set(case_identifiers)),
        "policy_identifiers": list(set(policy_identifiers)),
        "judges": list(set(judges))
    }
