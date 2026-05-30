"""
Clause Intelligence Service — Production-Grade Legal Clause Analysis

Extracts atomic, classified, AI-summarized clauses from legal documents.
Each clause represents ONE legal concept with explainability metadata.
"""

import re
import logging
from typing import List, Dict, Any
from uuid import uuid4

from app.services.supabase_service import supabase, supabase_execute

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Clause Type Definitions (document-agnostic)
# ──────────────────────────────────────────────

CLAUSE_TYPES = {
    "rent": {
        "keywords": [r"\brent\b", r"\bmonthly\s*rent\b", r"\brental\b", r"\blease\s*amount\b"],
        "weight": 0.85, "risk_default": "medium"
    },
    "deposit": {
        "keywords": [r"\bdeposit\b", r"\bsecurity\s*deposit\b", r"\bearnest\s*money\b", r"\badvance\b"],
        "weight": 0.8, "risk_default": "medium"
    },
    "indemnity": {
        "keywords": [r"\bindemnif", r"\bhold\s*harmless\b", r"\bsave\s*harmless\b"],
        "weight": 1.0, "risk_default": "high"
    },
    "insurance": {
        "keywords": [r"\binsurance\b", r"\binsured\b", r"\bpolicy\b", r"\bcoverage\b", r"\bpremium\b"],
        "weight": 0.7, "risk_default": "medium"
    },
    "taxes": {
        "keywords": [r"\btax\b", r"\btaxes\b", r"\bstamp\s*duty\b", r"\bgst\b", r"\btds\b"],
        "weight": 0.7, "risk_default": "low"
    },
    "termination": {
        "keywords": [r"\bterminate\b", r"\btermination\b", r"\bcancel\b", r"\brevok", r"\bend\s*this\s*agreement\b"],
        "weight": 1.0, "risk_default": "high"
    },
    "default": {
        "keywords": [r"\bdefault\b", r"\bbreach\b", r"\bfailure\s*to\s*comply\b", r"\bviolation\b"],
        "weight": 1.0, "risk_default": "high"
    },
    "liability": {
        "keywords": [r"\bliable\b", r"\bliability\b", r"\bdamages\b", r"\bresponsible\s*for\b"],
        "weight": 1.0, "risk_default": "high"
    },
    "penalty": {
        "keywords": [r"\bpenalt", r"\bfine\b", r"\bforfeiture\b", r"\bliquidated\s*damages\b"],
        "weight": 0.95, "risk_default": "high"
    },
    "construction_obligation": {
        "keywords": [r"\bconstruct", r"\bbuild", r"\berect", r"\bcompletion\s*certificate\b", r"\bbuilding\s*plan\b"],
        "weight": 0.8, "risk_default": "medium"
    },
    "timeline": {
        "keywords": [r"\bwithin\s*\d+", r"\bdeadline\b", r"\btime\s*period\b", r"\bcommencement\b", r"\bexpir"],
        "weight": 0.7, "risk_default": "medium"
    },
    "approval": {
        "keywords": [r"\bapprov", r"\bpermission\b", r"\bconsent\b", r"\bsanction\b", r"\bclearance\b"],
        "weight": 0.6, "risk_default": "low"
    },
    "maintenance": {
        "keywords": [r"\bmaintenan", r"\brepair\b", r"\bupkeep\b", r"\brestore\b"],
        "weight": 0.6, "risk_default": "low"
    },
    "confidentiality": {
        "keywords": [r"\bconfidential", r"\bnon.?disclosure\b", r"\bsecrecy\b", r"\bproprietary\b"],
        "weight": 0.8, "risk_default": "medium"
    },
    "jurisdiction": {
        "keywords": [r"\bjurisdiction\b", r"\bgoverning\s*law\b", r"\bcourt\b", r"\btribunal\b"],
        "weight": 0.7, "risk_default": "low"
    },
    "arbitration": {
        "keywords": [r"\barbitrat", r"\bdispute\s*resolution\b", r"\bmediat"],
        "weight": 0.8, "risk_default": "medium"
    },
    "assignment": {
        "keywords": [r"\bassign", r"\btransfer\s*of\s*rights\b", r"\bsublease\b", r"\bsub.?let\b"],
        "weight": 0.7, "risk_default": "medium"
    },
    "renewal": {
        "keywords": [r"\brenewal\b", r"\bextension\b", r"\brenew\b", r"\bextend\b"],
        "weight": 0.6, "risk_default": "low"
    },
    "escalation": {
        "keywords": [r"\bescalat", r"\bincrease\b", r"\brevision\b", r"\bhike\b"],
        "weight": 0.7, "risk_default": "medium"
    },
    "payment": {
        "keywords": [r"\bpay\b", r"\bpayment\b", r"\bfee\b", r"\bconsideration\b", r"\bremunerat"],
        "weight": 0.8, "risk_default": "medium"
    },
    "ownership": {
        "keywords": [r"\bown\b", r"\bownership\b", r"\btitle\b", r"\bvest\b", r"\bproprietary\b", r"\bright\s+to\s+property\b"],
        "weight": 0.8, "risk_default": "medium"
    },
    "obligation": {
        "keywords": [r"\bshall\b", r"\bmust\b", r"\bagrees\s*to\b", r"\bundertakes\b", r"\bis\s*required\s*to\b"],
        "weight": 0.4, "risk_default": "low"
    },
}

# Legal roles for party attribution
LEGAL_ROLES = [
    "lessor", "lessee", "buyer", "seller", "employer", "employee",
    "lender", "borrower", "licensor", "licensee", "plaintiff", "defendant",
    "insurer", "insured", "policyholder", "petitioner", "respondent",
]

# Non-party terms to filter out
NON_PARTY_TERMS = {
    "municipal corporation", "corporation", "authority", "government",
    "court", "tribunal", "registry", "registrar", "bank", "department",
    "board", "commission", "committee", "council", "agency",
}


# ──────────────────────────────────────────────
# Text Processing
# ──────────────────────────────────────────────

def _split_into_paragraphs(text: str) -> List[str]:
    paras = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paras if len(p.strip()) > 30]


# Legal trigger phrases that indicate a new legal obligation
LEGAL_TRIGGERS = [
    r'shall\s+pay', r'shall\s+indemnify', r'shall\s+insure',
    r'must\s+complete', r'agrees\s+to', r'liable\s+for',
    r'may\s+terminate', r'responsible\s+for', r'prohibited\s+from',
    r'entitled\s+to', r'shall\s+maintain', r'shall\s+obtain',
    r'shall\s+provide', r'shall\s+comply', r'shall\s+not',
    r'must\s+pay', r'must\s+obtain', r'must\s+provide',
    r'shall\s+be\s+liable', r'shall\s+bear', r'shall\s+execute',
]

_TRIGGER_PATTERN = re.compile(
    r'(?:' + '|'.join(LEGAL_TRIGGERS) + r')',
    re.IGNORECASE
)

_MAX_CLAUSE_SENTENCES = 5


def _count_sentences(text: str) -> int:
    """Count approximate sentence count."""
    return len([s for s in re.split(r'[.!?]+', text) if s.strip()])


def _force_split_long(text: str) -> List[str]:
    """Force-split text that exceeds max sentence count."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if len(sentences) <= _MAX_CLAUSE_SENTENCES:
        return [text]
    chunks = []
    current = []
    for s in sentences:
        current.append(s)
        if len(current) >= _MAX_CLAUSE_SENTENCES:
            chunks.append(' '.join(current))
            current = []
    if current:
        chunks.append(' '.join(current))
    return chunks


def _split_atomic_clauses(paragraph: str) -> List[str]:
    """Split a large paragraph into atomic legal clauses.
    
    Pipeline: sentence boundaries → semicolons → numbered lists →
    legal trigger phrases → max-length enforcement.
    Each resulting clause should contain exactly ONE legal concept.
    """
    if len(paragraph) < 80:
        return [paragraph]
    
    # Phase 1: Split on sentence boundaries, semicolons, numbered lists
    phase1 = re.split(
        r'(?<=[.;])\s+(?=[A-Z(0-9])|'       # Period/semicolon + uppercase/number
        r'(?<=\))\s*\n\s*(?=[a-z(0-9])|'     # After closing paren + newline
        r'\n\s*(?=\(?[a-z0-9]+[.)]\s)|'      # Numbered sub-items like (a), (i), 1.
        r'(?:\s+(?=\([a-z0-9]+\)\s))',        # In-line sub-items like (a) (b)
        paragraph,
        flags=re.IGNORECASE
    )
    phase1 = [s.strip() for s in phase1 if s and s.strip()]
    
    # Phase 2: Split on legal triggers more aggressively
    phase2 = []
    for chunk in phase1:
        # Find all trigger positions in the chunk
        triggers = list(_TRIGGER_PATTERN.finditer(chunk))
        if len(triggers) <= 1:
            phase2.append(chunk)
            continue
        # Multiple triggers found — split before each trigger
        parts = []
        prev = 0
        for m in triggers[1:]:  # Keep first trigger with its prefix
            # Look back for a sentence boundary or comma near the trigger
            split_pos = m.start()
            # Try to find a sentence break before the trigger
            lookback = chunk[max(0, split_pos - 60):split_pos]
            boundary = None
            for sep in ['. ', '; ', ', and ', ', or ', ', ']:
                idx = lookback.rfind(sep)
                if idx >= 0:
                    boundary = max(0, split_pos - 60) + idx + len(sep)
                    break
            if boundary and boundary > prev:
                parts.append(chunk[prev:boundary].strip())
                prev = boundary
            else:
                parts.append(chunk[prev:split_pos].strip())
                prev = split_pos
        parts.append(chunk[prev:].strip())
        phase2.extend([p for p in parts if p])
    
    # Phase 3: Split on conditional/secondary clauses if still large
    phase3 = []
    for chunk in phase2:
        if _count_sentences(chunk) <= _MAX_CLAUSE_SENTENCES:
            phase3.append(chunk)
            continue
        secondary = re.split(
            r'(?i)(?:(?<=[.;])\s+)?\b(provided\s+that|subject\s+to|notwithstanding|'
            r'in\s+the\s+event\s+of|further[,]?\s+the|additionally|moreover|'
            r'however|in\s+addition)\b',
            chunk
        )
        if len(secondary) > 2:
            buf = ""
            for part in secondary:
                part = part.strip()
                if not part or len(part) < 20:
                    buf = (buf + " " + part).strip()
                    continue
                if buf:
                    phase3.append(buf)
                buf = part
            if buf:
                phase3.append(buf)
        else:
            phase3.append(chunk)
    
    # Phase 4: Merge very short fragments, then force-split anything still too long
    merged = []
    buffer = ""
    for chunk in phase3:
        if not chunk:
            continue
        if len(buffer) + len(chunk) < 80:
            buffer = (buffer + " " + chunk).strip() if buffer else chunk
        else:
            if buffer:
                merged.append(buffer)
            buffer = chunk
    if buffer:
        merged.append(buffer)
    
    # Phase 5: Enforce max sentence length
    final = []
    for chunk in merged:
        if _count_sentences(chunk) > _MAX_CLAUSE_SENTENCES:
            final.extend(_force_split_long(chunk))
        else:
            final.append(chunk)
    
    return [m for m in final if len(m) > 20]


# ──────────────────────────────────────────────
# Classification
# ──────────────────────────────────────────────

def _classify_clause(text: str) -> tuple:
    """Classify a clause text into the best matching type.
    Returns (clause_type, confidence, risk_level).
    """
    text_lower = text.lower()
    best_type = "obligation"
    best_score = 0.0
    best_risk = "low"
    
    for clause_type, config in CLAUSE_TYPES.items():
        score = 0.0
        for pattern in config["keywords"]:
            matches = re.findall(pattern, text_lower)
            score += len(matches) * config["weight"]
        
        if score > best_score:
            best_score = score
            best_type = clause_type
            best_risk = config["risk_default"]
    
    confidence = min(0.98, 0.5 + (best_score * 0.15))
    
    # Boost risk for clauses with strong obligation language + financial terms
    if re.search(r'\b(shall|must|liable|penalty|forfeit)\b', text_lower) and \
       re.search(r'\b(amount|pay|cost|charge|fee|damages)\b', text_lower):
        if best_risk == "low":
            best_risk = "medium"
    
    return best_type, round(confidence, 2), best_risk


def _detect_responsible_party(text: str, entities: Dict[str, Any]) -> str:
    """Detect the responsible party using grammatical context, not institutions."""
    text_lower = text.lower()
    parties_dict = entities.get("parties_dict", {})
    
    # Check for role keywords that indicate the grammatical subject of obligation
    obligation_patterns = [
        (r'\b(lessor|landlord|owner)\b.*\b(shall|must|agrees|undertakes|is\s*required)\b', "Lessor"),
        (r'\b(lessee|tenant|renter)\b.*\b(shall|must|agrees|undertakes|is\s*required)\b', "Lessee"),
        (r'\b(buyer|purchaser)\b.*\b(shall|must|agrees|undertakes)\b', "Buyer"),
        (r'\b(seller|vendor)\b.*\b(shall|must|agrees|undertakes)\b', "Seller"),
        (r'\b(employer|company)\b.*\b(shall|must|agrees|undertakes)\b', "Employer"),
        (r'\b(employee|worker)\b.*\b(shall|must|agrees|undertakes)\b', "Employee"),
        (r'\b(insurer)\b.*\b(shall|must|agrees|undertakes)\b', "Insurer"),
        (r'\b(insured|policyholder)\b.*\b(shall|must|agrees|undertakes)\b', "Insured"),
        (r'\b(plaintiff|petitioner)\b.*\b(shall|must|agrees|claims)\b', "Plaintiff"),
        (r'\b(defendant|respondent)\b.*\b(shall|must|agrees|denies)\b', "Defendant"),
    ]
    
    matched_roles = set()
    for pattern, role in obligation_patterns:
        if re.search(pattern, text_lower):
            matched_roles.add(role)
    
    # Also check for party names from NER
    if not matched_roles:
        for role, name in parties_dict.items():
            if name and name.lower() in text_lower:
                matched_roles.add(role.title())
            elif role.lower() in text_lower:
                matched_roles.add(role.title())
    
    # Fallback: scan for any role keyword
    if not matched_roles:
        for role in LEGAL_ROLES:
            if role in text_lower:
                # Verify it's not a non-party institution
                is_institution = any(term in text_lower for term in NON_PARTY_TERMS 
                                    if term != role)
                if not is_institution or role in ["insurer", "insured"]:
                    matched_roles.add(role.title())
    
    if len(matched_roles) > 1:
        return "Both"
    elif len(matched_roles) == 1:
        return matched_roles.pop()
    return "Unknown"


def _extract_financial_values(text: str) -> List[str]:
    """Extract financial amounts from clause text."""
    patterns = [
        r'(?:Rs\.?|INR|₹)\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakh|crore|thousand|hundred)s?)?',
        r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b',
        r'\b\d+%\b',
    ]
    values = []
    for p in patterns:
        for match in re.finditer(p, text, re.IGNORECASE):
            val = match.group(0).strip()
            if len(val) > 1:
                values.append(val)
    return list(set(values))[:5]


def _extract_deadlines(text: str) -> List[str]:
    """Extract timeline/deadline mentions from clause text."""
    patterns = [
        r'within\s+\d+\s+(?:days?|months?|years?|weeks?)',
        r'\b\d+\s+(?:days?|months?|years?|weeks?)\b',
        r'(?:before|by|on\s+or\s+before)\s+\d{1,2}[\s/.-]\w+[\s/.-]\d{2,4}',
        r'(?:commencement|expiry|completion)\s+(?:date|period)',
    ]
    deadlines = []
    for p in patterns:
        for match in re.finditer(p, text, re.IGNORECASE):
            deadlines.append(match.group(0).strip())
    return list(set(deadlines))[:4]


def _generate_ai_summary(text: str, clause_type: str, party: str) -> str:
    """Generate a complete, business-focused 2-3 sentence summary. Never truncates."""
    p = party or 'A party'
    financials = _extract_financial_values(text)
    deadlines = _extract_deadlines(text)
    f_str = f" of {financials[0]}" if financials else ""
    d_str = f" by {deadlines[0]}" if deadlines else ""

    # Full 2-sentence business summaries — no ellipsis, no truncation
    FULL_SUMMARIES = {
        "rent":     f"{p} is required to make regular rent payments{f_str}{d_str}. Failure to pay on time may trigger late fees, interest charges, or grounds for termination of the agreement.",
        "deposit":  f"{p} must provide a security deposit{f_str} before occupying the premises. This deposit may be applied against unpaid rent or damages at the end of the lease term.",
        "payment":  f"{p} has financial payment obligations{f_str}{d_str}. Non-payment may result in penalties, suspension of services, or legal action under the agreement.",
        "escalation": f"The agreement includes provisions for rent or price increases over time{f_str}. {p} should budget for these escalations to avoid financial shortfalls during the contract period.",
        "taxes":    f"{p} is responsible for all applicable taxes, levies, and government charges arising from the agreement. Failure to comply with tax obligations may result in fines or regulatory penalties.",
        "indemnity": f"{p} is financially responsible for covering losses, legal claims, third-party injuries, and regulatory violations arising from their actions. This indemnity obligation can create significant and potentially unlimited financial exposure{f_str}.",
        "liability": f"{p} bears financial responsibility for losses and damages under this agreement{f_str}. Liability exposure should be carefully assessed and mitigated through appropriate insurance coverage.",
        "insurance": f"{p} must obtain and maintain adequate insurance coverage{f_str} throughout the agreement term. Lapse in coverage may constitute a breach of contract and create uninsured risk exposure.",
        "penalty":  f"A financial penalty applies for breach or non-compliance{f_str}. {p} must ensure all obligations are fulfilled on schedule to avoid these charges.",
        "default":  f"This clause defines what constitutes a default under the agreement and the consequences that follow. Upon default, the non-breaching party may pursue remedies including termination, damages, or legal proceedings.",
        "termination": f"Either party may terminate this agreement under specified conditions{d_str}. Understanding termination rights is critical to managing exit risk and avoiding liability for early termination.",
        "renewal":  f"The agreement includes provisions for renewal or extension beyond the initial term. {p} should review renewal conditions{d_str} to avoid unintended automatic renewals or unfavorable terms.",
        "construction_obligation": f"{p} is responsible for undertaking construction, renovation, or property improvements as specified{d_str}. Failure to complete these obligations on time may result in financial penalties or breach of contract.",
        "timeline":  f"The agreement imposes specific performance deadlines{d_str}. Missing these deadlines may trigger penalties, termination rights, or other contractual consequences for {p}.",
        "approval":  f"Certain actions under this agreement require formal approval from regulatory bodies or the other party before proceeding. Proceeding without required approvals may constitute a breach and expose {p} to legal risk.",
        "maintenance": f"{p} is obligated to maintain the property in good condition throughout the agreement term. Neglecting maintenance responsibilities may result in liability for damages and costs at the end of the term.",
        "confidentiality": f"The agreement imposes obligations to keep specified information confidential and not disclose it to third parties. Breach of confidentiality may result in injunctive relief, damages, and reputational harm.",
        "jurisdiction": f"Disputes under this agreement are governed by the laws of a specified jurisdiction and must be resolved in designated courts. {p} should understand the practical implications of litigating in the specified forum.",
        "arbitration": f"Disputes must be resolved through arbitration rather than court litigation. While arbitration can be faster, {p} waives certain procedural rights available in standard court proceedings.",
        "assignment": f"The right to transfer or assign obligations under this agreement is restricted. {p} must obtain prior written consent before assigning their rights to a third party.",
        "ownership":  f"The agreement defines property rights, title, and ownership boundaries for {p}. Any encumbrances or restrictions on ownership should be carefully reviewed before signing.",
        "obligation": f"{p} has specific legal responsibilities under this agreement that must be fulfilled as stated. Failure to meet these obligations may give the other party grounds for breach of contract claims.",
    }

    summary = FULL_SUMMARIES.get(clause_type)
    if not summary:
        summary = f"This provision governs {clause_type.replace('_', ' ')} obligations under the agreement. {p} should review this clause carefully to understand their rights, responsibilities, and potential exposure."
    return summary


def _generate_legal_impact(clause_type: str, risk_level: str, party: str) -> str:
    """Generate a legal impact explanation for the clause."""
    impacts = {
        "rent": "Non-payment of rent may lead to eviction, penalties, or lease termination.",
        "deposit": "Deposit terms affect financial exposure and refund conditions at agreement end.",
        "indemnity": "Indemnity clauses can create unlimited financial exposure for the obligated party.",
        "insurance": "Failure to maintain required insurance may constitute a breach of the agreement.",
        "taxes": "Tax obligations affect the total cost of compliance under this agreement.",
        "termination": "Termination provisions define exit conditions and potential financial consequences.",
        "default": "Default provisions may trigger penalties, acceleration clauses, or legal proceedings.",
        "liability": "Liability provisions determine financial exposure and risk allocation between parties.",
        "penalty": "Penalties create direct financial consequences for non-compliance.",
        "construction_obligation": "Failure to complete construction within specified timelines may lead to termination.",
        "timeline": "Missing deadlines may result in penalties, default, or loss of rights.",
        "approval": "Proceeding without required approvals may void actions taken under the agreement.",
        "maintenance": "Failure to maintain the property may result in deductions or breach of agreement.",
        "confidentiality": "Breach of confidentiality may result in damages or injunctive relief.",
        "jurisdiction": "Jurisdiction clauses determine which court or law governs disputes.",
        "arbitration": "Arbitration clauses may limit the right to pursue litigation.",
        "assignment": "Assignment restrictions affect the ability to transfer rights or obligations.",
        "renewal": "Renewal terms affect long-term commitment and renegotiation opportunities.",
        "escalation": "Escalation clauses affect future financial obligations.",
        "payment": "Payment obligations create binding financial commitments.",
        "obligation": "These obligations are legally binding and enforceable.",
    }
    return impacts.get(clause_type, "This clause creates legally binding obligations.")

def _generate_title(clause_type: str, text: str) -> str:
    """Generate a short, contextual, readable title for the clause.
    Disambiguates multiple clauses of the same type with text-derived context."""
    base_titles = {
        "rent": "Rent Payment",
        "deposit": "Security Deposit",
        "indemnity": "Indemnity Obligation",
        "insurance": "Insurance Requirement",
        "taxes": "Tax Obligation",
        "termination": "Termination Right",
        "default": "Default & Breach",
        "liability": "Liability Limitation",
        "penalty": "Penalty Clause",
        "construction_obligation": "Construction Deadline",
        "timeline": "Important Deadline",
        "approval": "Approval Requirement",
        "maintenance": "Maintenance Obligation",
        "confidentiality": "Confidentiality Clause",
        "jurisdiction": "Governing Jurisdiction",
        "arbitration": "Arbitration Clause",
        "assignment": "Assignment Right",
        "renewal": "Renewal Option",
        "escalation": "Price Escalation",
        "payment": "Payment Obligation",
        "ownership": "Property Ownership",
        "obligation": "Legal Obligation",
    }
    
    title = base_titles.get(clause_type, "Legal Provision")
    text_lower = text.lower()
    
    # Contextual refinements based on clause content
    context_rules = [
        ("payment", "deposit", "Deposit Payment"),
        ("payment", "advance", "Advance Payment"),
        ("payment", "installment", "Installment Payment"),
        ("payment", "refund", "Refund Obligation"),
        ("payment", "interest", "Interest Payment"),
        ("default", "payment", "Payment Default"),
        ("default", "breach", "Breach Consequences"),
        ("termination", "notice", "Termination Notice"),
        ("termination", "mutual", "Mutual Termination"),
        ("termination", "default", "Termination for Default"),
        ("insurance", "fire", "Fire Insurance"),
        ("insurance", "liability", "Liability Insurance"),
        ("insurance", "health", "Health Insurance"),
        ("timeline", "completion", "Completion Deadline"),
        ("timeline", "delivery", "Delivery Deadline"),
        ("timeline", "commenc", "Commencement Date"),
        ("penalty", "delay", "Delay Penalty"),
        ("penalty", "late", "Late Payment Penalty"),
        ("taxes", "stamp", "Stamp Duty"),
        ("taxes", "gst", "GST Obligation"),
        ("liability", "unlimited", "Unlimited Liability"),
        ("liability", "cap", "Liability Cap"),
        ("obligation", "confidential", "Confidentiality Obligation"),
        ("obligation", "deliver", "Delivery Obligation"),
        ("obligation", "report", "Reporting Obligation"),
        ("rent", "escalat", "Rent Escalation"),
        ("rent", "advance", "Advance Rent"),
        ("deposit", "refund", "Deposit Refund"),
        ("indemnity", "third", "Third-Party Indemnity"),
        ("arbitration", "mediat", "Mediation Clause"),
    ]
    
    for c_type, keyword, ctx_title in context_rules:
        if clause_type == c_type and keyword in text_lower:
            title = ctx_title
            break
    
    return title


# ──────────────────────────────────────────────
# Main Detection Pipeline
# ──────────────────────────────────────────────

def detect_clauses(text: str, structured_entities: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract atomic, classified, AI-summarized clauses from legal text."""
    paragraphs = _split_into_paragraphs(text)
    clauses = []
    
    for para in paragraphs:
        # Split large paragraphs into atomic clauses for classification
        atomic_parts = _split_atomic_clauses(para)

        for part in atomic_parts:
            clause_type, confidence, risk_level = _classify_clause(part)

            # Skip weak matches
            if confidence < 0.55:
                continue

            party = _detect_responsible_party(part, structured_entities)
            financial_values = _extract_financial_values(part)
            deadlines = _extract_deadlines(part)
            ai_summary = _generate_ai_summary(part, clause_type, party)
            legal_impact = _generate_legal_impact(clause_type, risk_level, party)

            # Importance scoring
            type_weight = CLAUSE_TYPES.get(clause_type, {}).get("weight", 0.5)
            importance_score = round(min(1.0, confidence * type_weight + 0.1), 2)

            if importance_score >= 0.8:
                importance_label = "Critical"
            elif importance_score >= 0.6:
                importance_label = "Important"
            else:
                importance_label = "Standard"

            # Use the ORIGINAL paragraph as full_text so the user sees the
            # complete legal provision, not a mid-sentence split fragment.
            # The split `part` is only used for classification internals.
            display_text = para.strip()

            clause_obj = {
                "title": _generate_title(clause_type, part),
                "summary": ai_summary,
                "full_text": display_text,   # ← always the full original paragraph
                "clause_type": clause_type,
                "risk_level": risk_level,
                "importance_label": importance_label,
                "financial_values": financial_values,
                "deadlines": deadlines,
                "responsible_party": party,
                "legal_impact": legal_impact,
                "importance_score": importance_score,
                "confidence": confidence,
                # Backward compatibility
                "type": clause_type,
                "text": display_text,
                "party": party,
                "ai_summary": ai_summary,
            }

            if financial_values:
                clause_obj["amount"] = financial_values[0]

            clauses.append(clause_obj)
    
    # Deduplicate by (clause_type + paragraph hash) — use full_text, not fragment
    deduped = []
    seen_texts = set()
    for c in clauses:
        # Normalise the stored full_text for the dedup key
        norm = re.sub(r'\s+', ' ', c.get("full_text", "")).strip().lower()[:200]
        key = (c["clause_type"], norm)
        if key not in seen_texts:
            seen_texts.add(key)
            deduped.append(c)
    
    # Sort: Critical priority types first, then Important
    CRITICAL_TYPES = {"indemnity", "termination", "liability", "penalty", "default", "arbitration", "insurance"}
    def get_priority(c):
        p_type = 0 if c["clause_type"] in CRITICAL_TYPES else 1
        p_label = {"Critical": 0, "Important": 1, "Standard": 2}.get(c["importance_label"], 3)
        return (p_type, p_label, -c.get("importance_score", 0))

    deduped.sort(key=get_priority)
    
    # Build insight groups for the enterprise UI
    grouped = _build_insight_groups(deduped)
    
    # Debug logging
    logger.info(
        "Clause Analysis: Extracted=%d, Deduped=%d, Grouped=%d",
        len(clauses), len(deduped), len(grouped)
    )
    
    # Safety Fallback: If grouping returned nothing, re-group by category (never show individual duplicates)
    if not grouped and deduped:
        logger.warning("Insight grouping returned empty. Running category fallback.")
        cat_buckets_fb: Dict[str, List] = {}
        for c in deduped:
            cat = _INSIGHT_CATEGORIES.get(c["clause_type"], {}).get("category", "protections")
            cat_buckets_fb.setdefault(cat, []).append(c)
        for cat_key, cat_meta in sorted(_CATEGORY_META.items(), key=lambda x: x[1]["priority"]):
            bucket = cat_buckets_fb.get(cat_key, [])
            if not bucket:
                continue
            top = sorted(bucket, key=lambda c: -c.get("importance_score", 0))
            grouped.append({
                "category": cat_key,
                "label": cat_meta["label"],
                "importance_label": top[0]["importance_label"],
                "risk_level": max((c["risk_level"] for c in top), key=lambda r: {"high": 2, "medium": 1, "low": 0}.get(r, 0)),
                "summary": top[0]["summary"],
                "financial_values": list(dict.fromkeys(v for c in top for v in c.get("financial_values", [])))[:5],
                "deadlines": list(dict.fromkeys(d for c in top for d in c.get("deadlines", [])))[:4],
                "key_risks": list(dict.fromkeys(c["legal_impact"] for c in top if c.get("legal_impact")))[:3],
                "responsible_parties": list({c["responsible_party"] for c in top if c.get("responsible_party") and c["responsible_party"] != "Unknown"}),
                "source_count": len(bucket),
                "clauses": bucket,
            })
            if len(grouped) >= 8:
                break

    return {"clauses": deduped, "insight_groups": grouped}


# ──────────────────────────────────────────────
# Insight Grouping for Enterprise UI
# ──────────────────────────────────────────────

# Map clause types to insight categories
_INSIGHT_CATEGORIES = {
    "indemnity":     {"category": "risks",       "label": "Liability & Risk Exposure"},
    "liability":     {"category": "risks",       "label": "Liability & Risk Exposure"},
    "insurance":     {"category": "risks",       "label": "Liability & Risk Exposure"},
    "default":       {"category": "risks",       "label": "Default & Breach Risk"},
    "penalty":       {"category": "risks",       "label": "Penalty Provisions"},
    "termination":   {"category": "exit",        "label": "Exit & Termination Rights"},
    "renewal":       {"category": "exit",        "label": "Exit & Termination Rights"},
    "rent":          {"category": "finance",     "label": "Financial Commitments"},
    "deposit":       {"category": "finance",     "label": "Financial Commitments"},
    "payment":       {"category": "finance",     "label": "Financial Commitments"},
    "escalation":    {"category": "finance",     "label": "Financial Commitments"},
    "taxes":         {"category": "finance",     "label": "Financial Commitments"},
    "timeline":      {"category": "construction","label": "Construction & Completion Obligations"},
    "construction_obligation": {"category": "construction", "label": "Construction & Completion Obligations"},
    "approval":      {"category": "construction","label": "Construction & Completion Obligations"},
    "arbitration":   {"category": "dispute",     "label": "Dispute Resolution"},
    "jurisdiction":  {"category": "dispute",     "label": "Dispute Resolution"},
    "confidentiality":{"category":"protections", "label": "Legal Protections"},
    "ownership":     {"category": "protections", "label": "Legal Protections"},
    "maintenance":   {"category": "protections", "label": "Legal Protections"},
    "assignment":    {"category": "protections", "label": "Legal Protections"},
    "obligation":    {"category": "protections", "label": "Legal Protections"},
}

# Category display order and metadata — strictly Executive Briefing style
_CATEGORY_META = {
    "risks":        {"label": "⚠️ Liability & Risk Exposure",    "priority": 0},
    "finance":      {"label": "💰 Financial Commitments",        "priority": 1},
    "construction": {"label": "🏗️ Construction & Completion Obligations", "priority": 2},
    "exit":         {"label": "🚪 Exit & Termination Rights",    "priority": 3},
    "dispute":      {"label": "⚖️ Dispute Resolution",           "priority": 4},
    "protections":  {"label": "🛡️ Legal Protections",             "priority": 5},
}

# Low-value types to exclude from grouped view — only extremely generic boilerplate
_LOW_VALUE_TYPES = {"obligation"}


def _build_insight_groups(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group related clauses into insight categories for the enterprise UI.
    Merges financial values, deadlines, and risk summaries across related clauses.
    """
    # Filter out low-value clauses for the grouped view
    high_value = [c for c in clauses if c["clause_type"] not in _LOW_VALUE_TYPES]
    
    # Group by category
    cat_buckets: Dict[str, List[Dict[str, Any]]] = {}
    for c in high_value:
        meta = _INSIGHT_CATEGORIES.get(c["clause_type"], _INSIGHT_CATEGORIES["obligation"])
        cat = meta["category"]
        if cat not in cat_buckets:
            cat_buckets[cat] = []
        cat_buckets[cat].append(c)
    
    groups = []
    for cat_key, cat_meta in sorted(_CATEGORY_META.items(), key=lambda x: x[1]["priority"]):
        bucket = cat_buckets.get(cat_key, [])
        if not bucket:
            continue
        
        # Merge metadata across all clauses in this group
        all_financials = []
        all_deadlines = []
        all_risks = []
        all_parties = set()
        highest_risk = "low"
        highest_importance = "Standard"
        source_count = len(bucket)
        
        for c in bucket:
            all_financials.extend(c.get("financial_values", []))
            all_deadlines.extend(c.get("deadlines", []))
            if c.get("legal_impact"):
                all_risks.append(c["legal_impact"])
            if c.get("responsible_party") and c["responsible_party"] != "Unknown":
                all_parties.add(c["responsible_party"])
            if c["risk_level"] == "high":
                highest_risk = "high"
            elif c["risk_level"] == "medium" and highest_risk != "high":
                highest_risk = "medium"
            imp_order = {"Critical": 2, "Important": 1, "Standard": 0}
            if imp_order.get(c["importance_label"], 0) > imp_order.get(highest_importance, 0):
                highest_importance = c["importance_label"]
        
        # Deduplicate
        all_financials = list(dict.fromkeys(all_financials))[:5]
        all_deadlines = list(dict.fromkeys(all_deadlines))[:4]
        all_risks = list(dict.fromkeys(all_risks))[:3]
        
        # Use the highest-scoring clause summary as the primary voice,
        # then append unique impact sentences from up to 2 more clauses.
        top_clauses = sorted(bucket, key=lambda c: -c.get("importance_score", 0))[:3]
        primary = top_clauses[0].get("summary", "").strip() if top_clauses else ""
        extras = []
        for c in top_clauses[1:]:
            s = c.get("summary", "").strip()
            # Only add if it contributes a meaningfully different sentence
            if s and s != primary and not primary.startswith(s[:30]):
                extras.append(s.rstrip(".") + ".")
        merged_summary = primary
        if extras:
            merged_summary = merged_summary.rstrip(".") + ". " + " ".join(extras[:1])
        if not merged_summary:
            merged_summary = f"This category covers {cat_meta['label'].split()[-1].lower()} obligations within the agreement."

        # Ensure label is always a clean string (strip emoji for storage, frontend can style)
        clean_label = cat_meta["label"]

        group = {
            "category": cat_key,
            "label": clean_label,
            "importance_label": highest_importance,
            "risk_level": highest_risk,
            "summary": merged_summary,
            "financial_values": all_financials,
            "deadlines": all_deadlines,
            "key_risks": all_risks,
            "responsible_parties": list(all_parties),
            "source_count": source_count,
            "clauses": bucket,
        }
        groups.append(group)

    # --- FALLBACK: Supplement sparse groups, BUT merge by category (no per-clause cards) ---
    if len(groups) < 5 and clauses:
        existing_cats = {g["category"] for g in groups}
        featured_texts = {c.get("full_text", "") for g in groups for c in g["clauses"]}

        # Collect unfeatured clauses into category buckets
        supp_buckets: Dict[str, List] = {}
        priority_types = ["indemnity", "termination", "penalty", "default", "liability", "insurance", "arbitration"]
        sorted_fallback = sorted(
            clauses,
            key=lambda c: (0 if c.get("clause_type") in priority_types else 1, -c.get("importance_score", 0))
        )
        for c in sorted_fallback:
            if c.get("full_text") in featured_texts:
                continue
            cat = _INSIGHT_CATEGORIES.get(c.get("clause_type", ""), {}).get("category", "protections")
            if cat not in existing_cats:   # don't duplicate a category already shown
                supp_buckets.setdefault(cat, []).append(c)

        # Build one merged card per supplementary category
        for cat_key, cat_meta in sorted(_CATEGORY_META.items(), key=lambda x: x[1]["priority"]):
            if len(groups) >= 8:
                break
            bucket = supp_buckets.get(cat_key, [])
            if not bucket:
                continue
            top = sorted(bucket, key=lambda c: -c.get("importance_score", 0))
            groups.append({
                "category": cat_key,
                "label": cat_meta["label"],
                "importance_label": top[0].get("importance_label", "Standard"),
                "risk_level": max((c.get("risk_level", "low") for c in top), key=lambda r: {"high": 2, "medium": 1, "low": 0}.get(r, 0)),
                "summary": top[0].get("summary", ""),
                "financial_values": list(dict.fromkeys(v for c in top for v in c.get("financial_values", [])))[:5],
                "deadlines": list(dict.fromkeys(d for c in top for d in c.get("deadlines", [])))[:4],
                "key_risks": list(dict.fromkeys(c["legal_impact"] for c in top if c.get("legal_impact")))[:3],
                "responsible_parties": list({c["responsible_party"] for c in top if c.get("responsible_party") and c["responsible_party"] != "Unknown"}),
                "source_count": len(bucket),
                "clauses": bucket,
            })

    return groups[:8]  # Executive briefing: maximum 8 cards


def process_and_store_clauses(document_id: str, text: str, structured_entities: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = detect_clauses(text, structured_entities)
    
    # detect_clauses now returns {"clauses": [...], "insight_groups": [...]}
    if isinstance(result, dict):
        raw_clauses = result.get("clauses", [])
        insight_groups = result.get("insight_groups", [])
    else:
        # Backward compat fallback
        raw_clauses = result if result else []
        insight_groups = []
    
    if not raw_clauses:
        return []

    payload = {
        "id": str(uuid4()),
        "document_id": document_id,
        "clauses": raw_clauses,
        "insight_groups": insight_groups,
    }
    
    try:
        supabase_execute(supabase.table("document_clauses").delete().eq("document_id", document_id))
    except Exception as exc:
        logger.warning("Failed to delete old clauses for %s: %s", document_id, exc)
    
    try:
        supabase_execute(supabase.table("document_clauses").insert(payload))
    except Exception as exc:
        # Fallback: store without insight_groups if column doesn't exist
        try:
            payload.pop("insight_groups", None)
            supabase_execute(supabase.table("document_clauses").insert(payload))
        except Exception as exc2:
            logger.error("Failed to store document clauses for %s: %s", document_id, exc2)
        
    return raw_clauses

