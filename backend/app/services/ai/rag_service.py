"""
RAG Service — Conversational Legal AI Assistant

Architecture:
  1. Intent Classifier   — route queries before retrieval
  2. Retrieval Layer     — semantic (Pinecone) + fallback (keyword)
  3. Reasoning Layer     — Gemini generation with intent-aware prompts
  4. Confidence Engine   — score based on retrieval quality
  5. Response Formatter  — clean output for the UI
"""

import logging
import re
from typing import List, Dict, Any, Tuple

from app.services.ai.embeddings import encode_texts
from app.services.ai.pinecone_store import upsert_vectors, get_index
from app.services.supabase_service import supabase, supabase_execute
from app.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Phase 1 — Intent Classification
# ──────────────────────────────────────────────

_GREETING_PATTERNS = re.compile(
    r'^\s*(hi|hello|hey|greetings|good\s*(morning|afternoon|evening|day)|'
    r'thanks|thank\s*you|bye|goodbye|howdy|sup|yo|namaste)\s*[!?.]*\s*$',
    re.IGNORECASE
)

_HELP_PATTERNS = re.compile(
    r'(what can you do|help me|how does this work|what are your capabilities|'
    r'explain features|what should i ask|guide me|show me what you can do|'
    r'how to use|what do you do)',
    re.IGNORECASE
)

_LEGAL_ANALYSIS_KEYWORDS = [
    'risk', 'dangerous', 'one-sided', 'unfair', 'negotiate', 'concern',
    'implication', 'ambiguity', 'ambiguous', 'loophole', 'red flag',
    'problematic', 'favorable', 'unfavorable', 'recommend', 'advise',
    'should i sign', 'safe to sign', 'protect', 'exposure', 'liability risk',
    'summarize liabilities', 'what should i', 'is this fair', 'bias',
]

_ENTITY_QUERY_PATTERNS = re.compile(
    r'(who are the parties|list.*(entit|part|names|organizations)|'
    r'tell.*(entit|part|names)|'
    r'what (organizations?|companies|dates?|locations?|amounts?|money|durations?|judges?|'
    r'legal references|case numbers?|policy numbers?) (are|is|were|exist|mentioned|present|listed|found|extracted)|'
    r'show.*(entit|part|names|dates?|locations?|amounts?)|'
    r'list all (parties|entities|names|dates|locations|amounts|organizations)|'
    r'(entities|party names|extracted data|entity names))',
    re.IGNORECASE
)

# Entity lookup: "who is X", "what is X", "identify X", "role of X"
_ENTITY_LOOKUP_PATTERNS = re.compile(
    r'^\s*(who\s+is|what\s+is|identify|role\s+of|tell\s+me\s+about|info\s+on|details\s+of|'
    r'who\s+is\s+the|what\s+is\s+the)\s+(.+)',
    re.IGNORECASE
)

# Prefixes to strip when extracting the entity search term
_ENTITY_TERM_PREFIXES = re.compile(
    r'^(who\s+is\s+the|who\s+is|what\s+is\s+the|what\s+is|identify\s+the|identify|'
    r'role\s+of\s+the|role\s+of|tell\s+me\s+about\s+the|tell\s+me\s+about|'
    r'info\s+on\s+the|info\s+on|details\s+of\s+the|details\s+of)\s+',
    re.IGNORECASE
)

# Role aliases for synonym resolution
_ROLE_ALIASES = {
    'landlord': 'lessor', 'tenant': 'lessee', 'renter': 'lessee',
    'owner': 'lessor', 'purchaser': 'buyer', 'vendor': 'seller',
    'claimant': 'insured', 'insurance company': 'insurer',
    'complainant': 'plaintiff', 'accused': 'defendant',
    'appellant': 'appellant', 'worker': 'employee', 'company': 'employer',
    'bank': 'lender', 'debtor': 'borrower',
}

# Known organization aliases
_ORG_ALIASES = {
    'bbmp': 'bruhat bengaluru mahanagara palike',
    'bda': 'bangalore development authority',
    'mcd': 'municipal corporation of delhi',
    'bmc': 'brihanmumbai municipal corporation',
    'rera': 'real estate regulatory authority',
    'sebi': 'securities and exchange board of india',
    'rbi': 'reserve bank of india',
}

_OFF_TOPIC_PATTERNS = re.compile(
    r'(weather|joke|cricket|football|movie|recipe|game|match|song|music|'
    r'who is the president|capital of|population of|how old are you|'
    r'what is your name|are you a robot|tell me something fun)',
    re.IGNORECASE
)


def classify_intent(query: str) -> str:
    """Classify user query intent before any retrieval."""
    q = query.strip()

    if _GREETING_PATTERNS.match(q):
        return 'greeting'

    if _HELP_PATTERNS.search(q):
        return 'help'

    if _OFF_TOPIC_PATTERNS.search(q):
        return 'off_topic'

    # Entity lookup: "who is X" / "what is X" (single entity resolution)
    if _ENTITY_LOOKUP_PATTERNS.match(q):
        return 'entity_lookup'

    # Entity listing: "list all entities" / "who are the parties"
    if _ENTITY_QUERY_PATTERNS.search(q):
        return 'entity_query'

    q_lower = q.lower()
    if any(kw in q_lower for kw in _LEGAL_ANALYSIS_KEYWORDS):
        return 'legal_analysis'

    # Default: treat as document Q&A
    return 'document_qa'


# ──────────────────────────────────────────────
# Phase 2A — Non-Retrieval Responses
# ──────────────────────────────────────────────

_GREETING_RESPONSE = (
    "Hello! I'm your AI legal assistant. I've analyzed this document and can help you understand "
    "its clauses, obligations, risks, payment terms, timelines, and legal implications.\n\n"
    "Feel free to ask me anything — for example:\n"
    "• What are the payment obligations?\n"
    "• What risks should I be aware of?\n"
    "• Can this agreement be terminated early?"
)

_HELP_RESPONSE = (
    "I can help you analyze and understand this legal document. Here are some things you can ask:\n\n"
    "**📋 Clauses & Terms**\n"
    "• What are the key terms of this agreement?\n"
    "• What is the notice period for termination?\n\n"
    "**💰 Financial Obligations**\n"
    "• What are the payment obligations?\n"
    "• Are there any penalties or late fees?\n\n"
    "**⚠️ Risks & Liabilities**\n"
    "• What are the major risks in this agreement?\n"
    "• Who bears liability for damages?\n\n"
    "**⏰ Timelines & Deadlines**\n"
    "• What are the important dates and deadlines?\n"
    "• When does this agreement expire?\n\n"
    "**🔍 Legal Analysis**\n"
    "• Is this agreement one-sided?\n"
    "• What should I negotiate before signing?"
)

_OFF_TOPIC_RESPONSE = (
    "I'm designed to assist with analysis of the uploaded legal document. "
    "I can help you understand clauses, risks, obligations, timelines, liabilities, and legal implications.\n\n"
    "Try asking something like:\n"
    "• What are the payment terms?\n"
    "• What risks does this agreement carry?"
)


def _non_retrieval_response(intent: str) -> Dict[str, Any]:
    """Generate responses that don't require document retrieval."""
    responses = {
        'greeting': _GREETING_RESPONSE,
        'help': _HELP_RESPONSE,
        'off_topic': _OFF_TOPIC_RESPONSE,
    }
    return {
        "answer": responses[intent],
        "confidence": None,
        "sources": [],
        "related_risks": [],
        "intent": intent,
    }


# ──────────────────────────────────────────────
# Entity Query Pipeline
# ──────────────────────────────────────────────

def _fetch_stored_entities(document_id: str) -> Dict[str, Any]:
    """Fetch structured entity data from the analysis_results table.
    
    Cross-references NER entities with the Gemini structured_summary
    for more accurate party-role mappings.
    """
    try:
        row = supabase_execute(
            supabase.table("analysis_results")
            .select("entities")
            .eq("document_id", document_id)
            .limit(1)
        ).data
        if row and row[0].get("entities"):
            entities_blob = row[0]["entities"]
            # The NER output lives in 'grouped' (or 'raw')
            grouped = entities_blob.get("grouped") or entities_blob.get("raw") or entities_blob
            
            # Cross-reference with structured_summary for better party accuracy
            structured_summary = entities_blob.get("structured_summary")
            if isinstance(structured_summary, dict):
                summary_parties = structured_summary.get("parties", [])
                if isinstance(summary_parties, list) and summary_parties:
                    # Parse "Lessor: Mr. Rajesh Kumar" style entries
                    summary_parties_dict = {}
                    for entry in summary_parties:
                        entry_str = str(entry).strip()
                        # Match patterns like "Lessor: Mr. Rajesh Kumar" or "Buyer - John Doe"
                        match = re.match(
                            r'^(Lessor|Lessee|Buyer|Seller|Employer|Employee|Lender|Borrower|'
                            r'Licensor|Licensee|Plaintiff|Defendant|Petitioner|Respondent|'
                            r'Insurer|Insured|Policyholder|Beneficiary|Appellant|'
                            r'First Party|Second Party|Party\s*[AB12])'
                            r'\s*[:\-–—]\s*(.+)',
                            entry_str, re.IGNORECASE
                        )
                        if match:
                            role = match.group(1).strip()
                            name = re.sub(r'^(Mr\.|Mrs\.|Ms\.|Dr\.|Shri|Smt\.?)\s*', '', match.group(2).strip())
                            name = name.strip()
                            if name:
                                summary_parties_dict[role.lower()] = name
                    
                    # Override NER parties_dict with more accurate summary data
                    if summary_parties_dict:
                        grouped["parties_dict"] = summary_parties_dict
                        logger.debug("Overrode NER parties_dict with structured_summary: %s", summary_parties_dict)
            
            return grouped
    except Exception as e:
        logger.warning("Failed to fetch stored entities: %s", e)
    return {}


def _format_entity_response(entities: Dict[str, Any], query: str) -> str:
    """Format structured entities into a human-readable response."""
    enriched = entities.get("enriched", {})
    parties_dict = entities.get("parties_dict", {})

    # Category config: (key, display_title, emoji)
    categories = [
        ("parties", "Parties & Individuals", "👤"),
        ("money", "Financial Amounts", "💰"),
        ("dates", "Important Dates", "📅"),
        ("durations", "Durations", "⏱️"),
        ("locations", "Locations & Jurisdictions", "📍"),
        ("legal_references", "Legal References", "📜"),
        ("case_identifiers", "Case Numbers", "🔢"),
        ("judges", "Judges", "⚖️"),
        ("policy_identifiers", "Policy & Claim IDs", "📋"),
    ]

    # Detect if user is asking about a specific category
    q_lower = query.lower()
    requested_categories = None
    category_keywords = {
        "parties": ["parties", "party", "names", "who", "lessor", "lessee", "buyer", "seller",
                    "employer", "employee", "plaintiff", "defendant", "organizations", "companies",
                    "entities", "entity"],
        "money": ["money", "amounts", "payment", "financial", "cost", "price", "fee"],
        "dates": ["dates", "date", "when", "timeline"],
        "durations": ["durations", "duration", "period", "how long"],
        "locations": ["locations", "location", "where", "jurisdiction", "place", "city", "address"],
        "legal_references": ["legal references", "acts", "sections", "law", "statute"],
        "case_identifiers": ["case numbers", "case no", "appeal", "suit"],
        "judges": ["judges", "judge", "justice", "hon"],
        "policy_identifiers": ["policy", "claim", "certificate"],
    }

    for cat_key, keywords in category_keywords.items():
        if any(kw in q_lower for kw in keywords):
            if requested_categories is None:
                requested_categories = []
            requested_categories.append(cat_key)

    # Build response
    sections = []
    display_categories = categories if requested_categories is None else [
        c for c in categories if c[0] in requested_categories
    ]

    for key, title, emoji in display_categories:
        # Prefer enriched data (has metadata like roles)
        enriched_items = enriched.get(key, [])
        simple_items = entities.get(key, [])

        if enriched_items:
            lines = []
            for item in enriched_items:
                text = item.get("text", "") if isinstance(item, dict) else str(item)
                if not text:
                    continue
                # Add role info for parties
                meta = item.get("metadata", {}) if isinstance(item, dict) else {}
                role = meta.get("role", "")
                money_type = meta.get("type", "")

                if role:
                    lines.append(f"• {text} — {role}")
                elif money_type and money_type != "amount":
                    context = meta.get("context", "")
                    label = f"• ₹{text} ({money_type})"
                    if context:
                        label += f" — {context}"
                    lines.append(label)
                else:
                    lines.append(f"• {text}")

            if lines:
                sections.append(f"**{emoji} {title}**\n" + "\n".join(lines))

        elif simple_items and isinstance(simple_items, list):
            items_text = [str(s) for s in simple_items if str(s).strip()]
            if items_text:
                lines = [f"• {t}" for t in items_text]
                sections.append(f"**{emoji} {title}**\n" + "\n".join(lines))

    # Also include relations if present and user asked broadly
    relations = entities.get("relations", [])
    if relations and requested_categories is None:
        rel_lines = []
        for rel in relations:
            party = rel.get("party", rel.get("amount", ""))
            rel_type = rel.get("type", "")
            relation = rel.get("relation", "")
            if party and relation:
                rel_lines.append(f"• {party} → {relation}")
        if rel_lines:
            sections.append("**🔗 Key Relationships**\n" + "\n".join(rel_lines[:8]))

    if not sections:
        return "No entities were extracted from this document yet. The document may still be processing, or no recognizable entities were found."

    header = "Here are the entities extracted from this document:\n\n"
    return header + "\n\n".join(sections)


def _handle_entity_query(document_id: str, question: str) -> Dict[str, Any]:
    """Handle entity_query intent using structured NER data."""
    entities = _fetch_stored_entities(document_id)

    if not entities:
        return {
            "answer": "Entity data is not available yet. The document may still be processing. Please try again in a moment.",
            "confidence": None,
            "sources": [],
            "related_risks": [],
            "intent": "entity_query",
        }

    answer = _format_entity_response(entities, question)
    return {
        "answer": answer,
        "confidence": None,
        "sources": [],
        "related_risks": [],
        "intent": "entity_query",
    }


# ──────────────────────────────────────────────
# Entity Lookup (Resolution) Pipeline
# ──────────────────────────────────────────────

def _extract_search_term(query: str) -> str:
    """Extract the entity name/term from a lookup query."""
    term = _ENTITY_TERM_PREFIXES.sub('', query.strip())
    # Remove trailing punctuation
    term = re.sub(r'[?.!]+$', '', term).strip()
    return term


def _resolve_entity(entities: Dict[str, Any], search_term: str) -> Dict[str, Any] | None:
    """
    Search structured entities for a match.
    Returns a dict with matched entity info, or None.
    Uses: exact match → partial match → role match → alias match.
    """
    enriched = entities.get("enriched", {})
    parties_dict = entities.get("parties_dict", {})
    term_lower = search_term.lower().strip()

    # Resolve alias for roles
    resolved_role = _ROLE_ALIASES.get(term_lower, term_lower)

    # Category labels for response context
    category_labels = {
        "parties": "party/individual",
        "money": "financial amount",
        "dates": "date",
        "durations": "duration",
        "locations": "location/jurisdiction",
        "legal_references": "legal reference",
        "case_identifiers": "case identifier",
        "judges": "judge",
        "policy_identifiers": "policy/claim identifier",
    }

    # 1. Role match via parties_dict ("lessor" → "Rajesh Kumar")
    for role, name in parties_dict.items():
        if role.lower() == resolved_role or role.lower() == term_lower:
            # Find the enriched entity for extra context
            enriched_match = None
            for p in enriched.get("parties", []):
                if isinstance(p, dict) and p.get("text", "").lower() == name.lower():
                    enriched_match = p
                    break
            return {
                "text": name,
                "role": role.title(),
                "category": "parties",
                "category_label": "party/individual",
                "match_type": "role",
                "metadata": enriched_match.get("metadata", {}) if enriched_match else {},
            }

    # 2. Search across all enriched categories
    for cat_key, cat_label in category_labels.items():
        items = enriched.get(cat_key, [])
        for item in items:
            if not isinstance(item, dict):
                continue
            item_text = item.get("text", "")
            item_lower = item_text.lower()
            meta = item.get("metadata", {})

            # Exact match
            if item_lower == term_lower:
                return {
                    "text": item_text,
                    "role": meta.get("role", ""),
                    "category": cat_key,
                    "category_label": cat_label,
                    "match_type": "exact",
                    "metadata": meta,
                }

            # Partial match (search term contained in entity or vice versa)
            if term_lower in item_lower or item_lower in term_lower:
                return {
                    "text": item_text,
                    "role": meta.get("role", ""),
                    "category": cat_key,
                    "category_label": cat_label,
                    "match_type": "partial",
                    "metadata": meta,
                }

    # 3. Organization alias match
    alias_expanded = _ORG_ALIASES.get(term_lower, "")
    if alias_expanded:
        for item in enriched.get("parties", []):
            if isinstance(item, dict):
                if alias_expanded in item.get("text", "").lower():
                    return {
                        "text": item["text"],
                        "role": item.get("metadata", {}).get("role", ""),
                        "category": "parties",
                        "category_label": "organization",
                        "match_type": "alias",
                        "metadata": item.get("metadata", {}),
                    }

    # 4. Fallback: search simple string lists
    for cat_key, cat_label in category_labels.items():
        simple_items = entities.get(cat_key, [])
        if not isinstance(simple_items, list):
            continue
        for s in simple_items:
            s_str = str(s).lower()
            if term_lower in s_str or s_str in term_lower:
                return {
                    "text": str(s),
                    "role": "",
                    "category": cat_key,
                    "category_label": cat_label,
                    "match_type": "simple",
                    "metadata": {},
                }

    return None


def _build_entity_lookup_response(match: Dict[str, Any], search_term: str, entities: Dict[str, Any]) -> str:
    """Build a natural language response for a resolved entity."""
    text = match["text"]
    role = match.get("role", "")
    category = match["category"]
    cat_label = match["category_label"]
    meta = match.get("metadata", {})

    # Party with role
    if category == "parties" and role:
        response = f"**{text}** is identified in this document as the **{role}**."
        # Check for related obligations
        relations = entities.get("relations", [])
        obligations = [r for r in relations if r.get("party", "").lower() == text.lower()]
        if obligations:
            response += "\n\nKey obligations found:"
            for ob in obligations[:4]:
                response += f"\n• {ob.get('relation', '')}"
        return response

    # Party without role (organization)
    if category == "parties":
        return f"**{text}** is mentioned in this document as a {cat_label}."

    # Money
    if category == "money":
        m_type = meta.get("type", "amount")
        context = meta.get("context", "")
        resp = f"**₹{text}** is identified as a **{m_type}** in this document."
        if context:
            resp += f"\n\nContext: \"{context}\""
        return resp

    # Dates
    if category == "dates":
        return f"**{text}** is an important date mentioned in this document."

    # Locations
    if category == "locations":
        return f"**{text}** is a location/jurisdiction referenced in this document."

    # Legal references
    if category == "legal_references":
        return f"**{text}** is a legal reference cited in this document."

    # Generic
    return f"**{text}** is identified as a {cat_label} in this document."


def _handle_entity_lookup(document_id: str, question: str) -> Dict[str, Any] | None:
    """
    Handle entity_lookup intent. Returns structured response or None to trigger fallback.
    """
    entities = _fetch_stored_entities(document_id)
    if not entities:
        return None  # Trigger fallback to retrieval

    search_term = _extract_search_term(question)
    if not search_term or len(search_term) < 2:
        return None  # Too short, fall back

    match = _resolve_entity(entities, search_term)
    if not match:
        return None  # Not found, fall back to retrieval

    answer = _build_entity_lookup_response(match, search_term, entities)
    return {
        "answer": answer,
        "confidence": None,
        "sources": [],
        "related_risks": [],
        "intent": "entity_lookup",
    }


# ──────────────────────────────────────────────
# Retrieval Layer (unchanged core logic)
# ──────────────────────────────────────────────

def store_clauses_in_pinecone(document_id: str, clauses: List[Dict[str, Any]]):
    if not clauses:
        return

    texts = [clause.get("text", "") for clause in clauses]
    embeddings = encode_texts(texts)

    if len(embeddings) == 0:
        return

    vectors = []
    for i, clause in enumerate(clauses):
        vector_id = f"{document_id}_clause_{i}"
        meta = {
            "document_id": document_id,
            "clause_type": clause.get("type", ""),
            "party": clause.get("party", ""),
            "text": clause.get("text", "")
        }
        vectors.append((vector_id, embeddings[i].tolist(), meta))

    upsert_vectors(vectors)


def _retrieve_sources(document_id: str, question: str, top_k: int = 5) -> Tuple[List[Dict], float, str]:
    """Retrieve relevant clauses via Pinecone or fallback keyword search."""
    index = get_index()
    sources = []
    total_score = 0.0
    rag_mode = "semantic"

    if index:
        try:
            query_emb = encode_texts([question])[0].tolist()
            results = index.query(
                vector=query_emb,
                top_k=top_k,
                include_metadata=True,
                filter={"document_id": document_id}
            )

            seen_texts = set()
            for match in results.get("matches", []):
                meta = match.get("metadata", {})
                text = meta.get("text", "").strip()
                score = match.get("score", 0.0)

                if text and text not in seen_texts:
                    seen_texts.add(text)
                    total_score += score
                    sources.append({
                        "text": text,
                        "clause_type": meta.get("clause_type", ""),
                        "party": meta.get("party", ""),
                        "score": round(score, 4),
                        "importance_label": meta.get("importance_label", "Standard")
                    })
        except Exception as e:
            logger.warning("Semantic search failed, falling back to keyword search: %s", e)
            index = None

    if not index:
        rag_mode = "keyword"
        try:
            row = supabase_execute(
                supabase.table("document_clauses")
                .select("clauses")
                .eq("document_id", document_id)
                .limit(1)
            ).data
            if row and row[0].get("clauses"):
                all_clauses = row[0].get("clauses", [])
                query_words = set(w for w in question.lower().split() if len(w) > 3)

                scored_clauses = []
                for c in all_clauses:
                    c_text = c.get("text", "").lower()
                    overlap = sum(1 for w in query_words if w in c_text)
                    if overlap > 0:
                        score = min(0.9, overlap * 0.15)
                        scored_clauses.append({
                            "text": c.get("text", ""),
                            "clause_type": c.get("type", ""),
                            "party": c.get("party", ""),
                            "score": score,
                            "importance_label": c.get("importance_label", "Standard")
                        })
                scored_clauses.sort(key=lambda x: x["score"], reverse=True)
                sources = scored_clauses[:top_k]
                total_score = sum(s["score"] for s in sources)
        except Exception as e:
            logger.warning("Keyword search failed: %s", e)

    return sources, total_score, rag_mode


def _fetch_related_risks(document_id: str, sources: List[Dict]) -> List[Dict]:
    """Fetch risks that overlap with retrieved source clauses."""
    related_risks = []
    try:
        row = supabase_execute(
            supabase.table("document_risks")
            .select("risks")
            .eq("document_id", document_id)
            .limit(1)
        ).data

        if row and row[0].get("risks"):
            risks_data = row[0].get("risks", {})
            all_risks = risks_data.get("high_risks", []) + risks_data.get("medium_risks", [])

            for r in all_risks:
                risk_text = r.get("clause_text", "")
                if any(s["text"] in risk_text or risk_text in s["text"] for s in sources if len(s["text"]) > 10):
                    related_risks.append(r)
    except Exception as exc:
        logger.warning("Failed to fetch risks for RAG: %s", exc)

    return related_risks


# ──────────────────────────────────────────────
# Reasoning Layer — Intent-Aware Prompts
# ──────────────────────────────────────────────

def _build_document_qa_prompt(question: str, context_text: str, risk_text: str) -> str:
    return f"""You are a professional legal assistant helping a user understand their legal document.

RULES:
- Answer ONLY based on the provided context.
- Use plain, clear English. Avoid legal jargon unless necessary.
- Be concise but thorough.
- If the answer is not in the context, say: "Based on the uploaded document, I could not find a clear clause addressing this question."
- Do NOT hallucinate or invent information.
- Reference specific clauses when possible.
- If a clause is marked (Importance: Critical), highlight it as **[CRITICAL]**.

Context from the document:
{context_text}{risk_text}

User's question:
{question}

Provide a clear, helpful answer:"""


def _build_legal_analysis_prompt(question: str, context_text: str, risk_text: str) -> str:
    return f"""You are an expert legal analyst reviewing a legal document for a client.

RULES:
- Provide analytical insights, not just factual answers.
- Identify potential risks, ambiguities, and one-sided obligations.
- Highlight clauses that could be problematic for either party.
- Suggest areas that may need negotiation or legal review.
- Use professional but accessible language.
- Ground every insight in the provided context — do NOT speculate.
- If a clause is marked (Importance: Critical), format it as **[CRITICAL]**.

Relevant clauses from the document:
{context_text}{risk_text}

User's analysis request:
{question}

Provide a thorough legal analysis:"""


def _call_gemini(prompt: str) -> str:
    """Call Gemini API and return generated text."""
    import httpx

    if not settings.gemini_api_key:
        return "AI model is not configured. Please check the API key settings."

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model_name}:generateContent"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "topK": 1}
        }
        with httpx.Client(timeout=60.0) as client:
            res = client.post(url, params={"key": settings.gemini_api_key}, json=body)
            res.raise_for_status()
            data = res.json()

            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "I was unable to generate an answer.")
        return "I was unable to generate an answer."
    except Exception as exc:
        logger.exception("Gemini API error")
        return "I encountered an error while analyzing the document. Please try again."


# ──────────────────────────────────────────────
# Confidence Engine
# ──────────────────────────────────────────────

def _calculate_confidence(sources: List[Dict], total_score: float) -> float:
    """Calculate confidence based on retrieval quality metrics."""
    if not sources:
        return 0.0

    avg_score = total_score / len(sources)
    # Bonus for having multiple supporting sources
    coverage_bonus = min(0.15, len(sources) * 0.04)
    # Bonus for having high-importance sources
    critical_bonus = 0.05 if any(s.get("importance_label") == "Critical" for s in sources) else 0.0

    confidence = avg_score + coverage_bonus + critical_bonus
    return round(min(0.98, max(0.1, confidence)), 2)


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

def query_rag(document_id: str, question: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Main RAG entry point with intent-aware routing.
    Returns a structured response with intent metadata for the UI.
    """
    # Step 1: Classify intent
    intent = classify_intent(question)

    # Step 2: Non-retrieval intents → respond immediately
    if intent in ('greeting', 'help', 'off_topic'):
        return _non_retrieval_response(intent)

    # Step 2b: Entity listing → use structured NER data directly
    if intent == 'entity_query':
        return _handle_entity_query(document_id, question)

    # Step 2c: Entity lookup (resolution) → search then fallback to retrieval
    if intent == 'entity_lookup':
        result = _handle_entity_lookup(document_id, question)
        if result:
            return result
        # Fallback: entity not found in structured data, try retrieval
        intent = 'document_qa'

    # Step 3: Retrieval-based intents (document_qa, legal_analysis)
    sources, total_score, rag_mode = _retrieve_sources(document_id, question, top_k)

    if not sources:
        return {
            "answer": "Based on the uploaded document, I could not find relevant clauses to answer this question. "
                      "Try rephrasing your question or asking about specific terms, obligations, or parties in the agreement.",
            "confidence": 0.0,
            "sources": [],
            "related_risks": [],
            "intent": intent,
        }

    # Step 4: Build context
    context_text = "\n\n".join([
        f"[{s['clause_type'].upper()}] (Importance: {s.get('importance_label', 'Standard')}) {s['text']}"
        for s in sources
    ])

    related_risks = _fetch_related_risks(document_id, sources)
    risk_text = ""
    if related_risks:
        risk_text = "\n\nKNOWN RISKS IN THIS CONTEXT:\n"
        for r in related_risks:
            risk_text += f"- {r.get('risk_type', '').upper()} RISK ({r.get('severity', '')}): {r.get('explanation', '')}\n"

    # Step 5: Generate answer with intent-appropriate prompt
    if intent == 'legal_analysis':
        prompt = _build_legal_analysis_prompt(question, context_text, risk_text)
    else:
        prompt = _build_document_qa_prompt(question, context_text, risk_text)

    answer = _call_gemini(prompt)

    # Step 6: Calculate confidence
    confidence = _calculate_confidence(sources, total_score)

    return {
        "answer": answer,
        "confidence": confidence,
        "sources": sources,
        "related_risks": related_risks,
        "intent": intent,
    }
