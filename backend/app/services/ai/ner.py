from __future__ import annotations

import logging
import re
import threading
from typing import Any, Dict, List, Set, Tuple

import spacy
from spacy.tokens import Span

from app.config import settings

logger = logging.getLogger(__name__)

# --- Configuration & Constants ---

_LABEL_TO_BUCKET = {
    'PERSON': 'parties',
    'ORG': 'parties',
    'DATE': 'dates',
    'MONEY': 'money',
    'GPE': 'locations',
    'LOC': 'locations',
    'LAW': 'legal_references',
}

ROLES = [
    "Lessor", "Lessee", "Buyer", "Seller", "Employer", "Employee",
    "Lender", "Borrower", "Licensor", "Licensee", "Disclosing Party", "Receiving Party",
    "Plaintiff", "Defendant", "Petitioner", "Respondent", "Appellant",
    "Insurer", "Insured", "Policyholder", "Beneficiary"
]

GENERIC_WORDS = {
    "schedule", "lease", "incidental", "agreement", "contract", "parties", 
    "party", "document", "deed", "annexure", "exhibit", "clause", "section"
}

PREFIXES_TO_REMOVE = [
    "lessee ", "lessor ", "mr. ", "mrs. ", "ms. ", "the ", "buyer ", "seller ", 
    "plaintiff ", "defendant ", "said ", "above-named "
]

REGEX_PATTERNS = {
    "legal_references": r'(Section\s\d+[A-Za-z]*\s(?:of\s\w+)?|Act,\s\d{4}|[A-Z][\w\s]+Act)',
    "case_identifiers": r'(Case\sNo\.?|Appeal\sNo\.?|Writ\sPetition\s\(C\)\sNo\.?|Suit\sNo\.?)\s?\d+/?\d*',
    "policy_identifiers": r'(Policy\sNo\.?|Claim\sID|Certificate\sNo\.?)\s?:?\s?[\w-]+',
    "judges": r'(Justice|Hon\.?ble|Judge)\s[A-Z][a-z]+(?:\s[A-Z][a-z]+)*',
    "durations": r'\b(\d+\s+(?:years?|months?|days?|weeks?))\b',
}

_nlp_loaded = None
_nlp_failed = False
_nlp_lock = threading.Lock()

# --- Internal Helpers ---

def _nlp():
    global _nlp_loaded, _nlp_failed
    if _nlp_failed: return None
    if _nlp_loaded is not None: return _nlp_loaded
    with _nlp_lock:
        if _nlp_failed: return None
        if _nlp_loaded is not None: return _nlp_loaded
        try:
            _nlp_loaded = spacy.load(settings.spacy_model, exclude=['tagger', 'parser', 'lemmatizer'])
            # Add sentencizer since we excluded the parser (needed for ent.sent)
            if 'sentencizer' not in _nlp_loaded.pipe_names:
                _nlp_loaded.add_pipe('sentencizer')
            return _nlp_loaded
        except Exception as exc:
            _nlp_failed = True
            logger.error("spaCy model '%s' failed: %s", settings.spacy_model, exc)
            return None

def _normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text)).strip()

def _clean_entity_text(text: str) -> str:
    t = text.strip()
    t_lower = t.lower()
    for p in PREFIXES_TO_REMOVE:
        if t_lower.startswith(p):
            t = t[len(p):].strip()
            t_lower = t.lower()
    t = re.sub(r'[:;,]$', '', t)
    return t

def _detect_role(ent: Span, doc_text: str) -> str | None:
    # Try sentence-level context first; fall back to proximity window
    try:
        sent_text = ent.sent.text.lower()
        for role in ROLES:
            if role.lower() in sent_text:
                return role
    except ValueError:
        pass  # Sentence boundaries unavailable — use proximity fallback

    start = max(0, ent.start_char - 80)
    end = min(len(doc_text), ent.end_char + 80)
    context = doc_text[start:end].lower()
    for role in ROLES:
        if role.lower() in context:
            return role
    return None

def _is_valid_date(text: str) -> bool:
    return bool(re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|20\d{2}|19\d{2})', text, re.I))

def _normalize_date(text: str) -> str:
    norm = re.sub(r'(?:st|nd|rd|th)\s+day\s+of\s+', ' ', text, flags=re.I)
    norm = re.sub(r',', '', norm)
    return re.sub(r'\s+', ' ', norm).strip()

def _detect_money_context(text: str, start_idx: int, end_idx: int) -> Tuple[str, str]:
    """Detect money type and broader context."""
    window_start = max(0, start_idx - 60)
    window_end = min(len(text), end_idx + 60)
    context_window = text[window_start:window_end].lower()
    
    types = ["rent", "deposit", "penalty", "compensation", "premium", "salary", "tax", "damages", "loan amount"]
    detected_type = "amount"
    for t in types:
        if t in context_window:
            detected_type = t
            break
            
    # Broader context (purpose)
    context_sentence = ""
    # Try to find a meaningful snippet
    match = re.search(r'([^.;]*' + re.escape(text[start_idx:end_idx]) + r'[^.;]*)', text[window_start:window_end])
    if match:
        context_sentence = match.group(0).strip()
        
    return detected_type, context_sentence

def _calculate_confidence(ent_type: str, text: str, source: str, context_valid: bool = False) -> float:
    base = 0.85 if source == "nlp" else 0.92
    if context_valid: base += 0.05
    if len(text) > 5 and not any(c.isdigit() for c in text): base += 0.03
    return min(0.99, base)

def _extract_relations(text: str, parties: List[Dict], results: Dict) -> List[Dict]:
    """Lightweight relation extraction for obligations and purposes."""
    relations = []
    text_lower = text.lower()
    
    # Party -> Obligation patterns
    obligation_keywords = ["shall pay", "must provide", "agrees to", "is responsible for", "shall maintain"]
    for party in parties:
        p_name = party["text"]
        p_idx = text_lower.find(p_name.lower())
        if p_idx == -1: continue
        
        # Look ahead for obligation keywords
        snippet = text_lower[p_idx:p_idx + 150]
        for kw in obligation_keywords:
            if kw in snippet:
                # Find the rest of the sentence as the obligation
                end_idx = snippet.find(".", snippet.find(kw))
                if end_idx == -1: end_idx = 100
                obligation = snippet[snippet.find(kw):end_idx].strip()
                relations.append({
                    "party": p_name,
                    "type": "obligation",
                    "relation": obligation,
                    "confidence": 0.75
                })
                break
                
    # Amount -> Purpose
    for money in results.get("money", []):
        if money["metadata"].get("context"):
            relations.append({
                "amount": money["text"],
                "type": "purpose",
                "relation": money["metadata"]["context"],
                "confidence": 0.8
            })
            
    # Party -> Risk patterns
    risk_keywords = ["unlimited liability", "indemnity", "indemnify", "liquidated damages", "termination without cause"]
    for party in parties:
        p_name = party["text"]
        p_idx = text_lower.find(p_name.lower())
        if p_idx == -1: continue
        
        snippet = text_lower[p_idx:p_idx + 200]
        for kw in risk_keywords:
            if kw in snippet:
                relations.append({
                    "party": p_name,
                    "type": "risk",
                    "relation": f"Associated with {kw}",
                    "confidence": 0.7
                })
                
    return relations

# --- Main Functions ---

def extract_entities(text: str, doc_type: str = "Generic") -> Dict[str, Any]:
    """
    Upgraded NER engine with context-aware intelligence and confidence scoring.
    Returns enriched objects and maintains keys for backward compatibility.
    """
    # Raw results as objects
    enriched_results: Dict[str, List[Dict]] = {
        "parties": [], "money": [], "dates": [], "durations": [],
        "locations": [], "legal_references": [], "case_identifiers": [],
        "policy_identifiers": [], "judges": []
    }
    
    # Backward compatibility lists (strings)
    simple_results: Dict[str, List[str]] = {k: [] for k in enriched_results.keys()}
    
    if not text or not str(text).strip():
        return {**simple_results, "enriched": enriched_results}

    nlp = _nlp()
    normalized = _normalize_text(text)
    doc = nlp(normalized[: settings.ner_max_chars]) if nlp else None

    seen_keys: Dict[str, Set[str]] = {k: set() for k in enriched_results.keys()}

    # 1. SpaCy Extraction
    if doc:
        for ent in doc.ents:
            bucket = _LABEL_TO_BUCKET.get(ent.label_)
            if not bucket: continue
            
            clean_val = _clean_entity_text(ent.text)
            if not clean_val or len(clean_val) < 2 or clean_val.lower() in GENERIC_WORDS:
                continue

            metadata = {}
            confidence = _calculate_confidence(bucket, clean_val, "nlp")

            if bucket == 'parties':
                if any(kw in clean_val.lower() for kw in ['act', 'section', 'article', 'rule']):
                    bucket = 'legal_references'
                else:
                    role = _detect_role(ent, normalized)
                    if role: 
                        metadata["role"] = role
                        confidence += 0.05
            
            elif bucket == 'dates':
                if not _is_valid_date(clean_val): continue
                clean_val = _normalize_date(clean_val)
                
            elif bucket == 'money':
                # Strip currency symbols and commas for the numeric part
                numeric_val = re.sub(r'[^\d.]', '', clean_val)
                m_type, m_ctx = _detect_money_context(normalized, ent.start_char, ent.end_char)
                metadata["type"] = m_type
                metadata["context"] = m_ctx
                # Keep numeric_val for simple results to ensure .isdigit() compatibility
                clean_val = numeric_val

            key = f"{clean_val.lower()}_{bucket}"
            if key not in seen_keys[bucket]:
                seen_keys[bucket].add(key)
                obj = {
                    "text": clean_val,
                    "type": bucket,
                    "confidence": round(confidence, 2),
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                    "metadata": metadata
                }
                enriched_results[bucket].append(obj)
                
                # Simple string for backward compatibility
                display_val = clean_val
                if "role" in metadata: display_val += f" ({metadata['role']})"
                elif "type" in metadata and bucket == "money": display_val += f" ({metadata['type']})"
                simple_results[bucket].append(display_val)

    # 2. Regex Extraction
    for category, pattern in REGEX_PATTERNS.items():
        for match in re.finditer(pattern, normalized, re.I):
            val = _clean_entity_text(match.group(0))
            if category == 'dates': val = _normalize_date(val)
            
            key = f"{val.lower()}_{category}"
            if key not in seen_keys[category] and val.lower() not in GENERIC_WORDS:
                seen_keys[category].add(key)
                confidence = _calculate_confidence(category, val, "regex")
                obj = {
                    "text": val,
                    "type": category,
                    "confidence": round(confidence, 2),
                    "start_char": match.start(),
                    "end_char": match.end(),
                    "metadata": {}
                }
                enriched_results[category].append(obj)
                simple_results[category].append(val)

    # 3. Relation Extraction
    relations = _extract_relations(normalized, enriched_results["parties"], enriched_results)

    # Combine for final output
    final_output = {
        **simple_results,  # Backward compatibility
        "enriched": enriched_results,
        "relations": relations
    }
    
    # Special backward compatibility key used in clause detection
    final_output["parties_dict"] = {
        p["metadata"]["role"].lower(): p["text"] 
        for p in enriched_results["parties"] 
        if "role" in p["metadata"]
    }

    return final_output

def entities_for_ui(text: str, doc_type: str = "Generic") -> Dict[str, Any]:
    return extract_entities(text, doc_type)
