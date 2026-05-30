import json
import logging
import re
from dataclasses import dataclass, field
import asyncio
import httpx
import random

from app.config import settings
from app.services.ai.text_cleaning import count_words

logger = logging.getLogger(__name__)
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

@dataclass
class SummaryResult:
    route: str
    word_count: int
    chunks: list
    partial_summaries: list
    final_summary: str
    extractive_summary: str
    extractive_sentences: list
    structured_summary: dict = field(default_factory=dict)

class GeminiClient:
    @staticmethod
    def _candidate_models(model_name):
        configured = [
            model_name,
            getattr(settings, "gemini_model_name", None),
            "gemini-2.5-flash",
            "gemini-1.5-flash-002",
        ]
        ordered = []
        seen = set()
        for item in configured:
            value = str(item or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    async def generate(self, prompt, model_name=None, timeout_seconds=None):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        timeout = timeout_seconds or settings.gemini_timeout_seconds
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "topP": 0.1, "topK": 1},
        }
        retries = min(3, max(1, int(settings.gemini_max_retries or 3)))
        base_backoff = float(settings.gemini_rate_limit_backoff_seconds or 15.0)
        models = self._candidate_models(model_name or settings.gemini_model_name)
        last_error = None

        for model in models:
            for attempt in range(1, retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(
                            API_URL.format(model=model),
                            params={"key": settings.gemini_api_key},
                            json=body,
                        )
                    if response.status_code == 404:
                        break
                    if response.status_code == 429:
                        if attempt < retries:
                            sleep_for = (base_backoff * attempt) + random.uniform(1.0, 3.0)
                            await asyncio.sleep(sleep_for)
                            continue
                        else:
                            last_error = RuntimeError(f"429 rate limit on {model}")
                            break
                    response.raise_for_status()
                    payload = response.json()
                    for candidate in payload.get("candidates") or []:
                        content = candidate.get("content") or {}
                        for part in content.get("parts") or []:
                            text = (part.get("text") or "").strip()
                            if text:
                                return text
                    raise RuntimeError("Gemini response did not contain text")
                except Exception as exc:
                    last_error = exc
                    if attempt < retries:
                        await asyncio.sleep(base_backoff + random.uniform(1.0, 3.0))
                        continue
                    break

        raise RuntimeError(f"Gemini generation failed: {last_error}")

gemini_client = GeminiClient()

def _detect_subtype(text, document_type):
    t = (document_type or "").lower()
    text_lower = text.lower()
    
    # Universal check for Loan Agreements across types
    if "loan agreement" in text_lower or "facility agreement" in text_lower or (("loan" in text_lower or "facility" in text_lower) and ("borrower" in text_lower or "lender" in text_lower)):
        return "loan_agreement"
        
    if t == "contract":
        if "lease" in text_lower or "rent" in text_lower: return "lease_agreement"
        if "employment" in text_lower or "salary" in text_lower: return "employment_contract"
        if "service" in text_lower or "deliverable" in text_lower: return "service_agreement"
        return "general_contract"
    if t == "property":
        if "sale deed" in text_lower: return "sale_deed"
        if "agreement to sell" in text_lower: return "agreement_to_sell"
        if "lease" in text_lower or "rent" in text_lower: return "lease_property"
        return "property_general"
    if t == "court_judgment":
        if "petition" in text_lower: return "petition_case"
        if "appeal" in text_lower: return "appeal_case"
        return "civil_criminal_judgment"
    if t == "insurance" or t == "financial":
        if "health" in text_lower or "mediclaim" in text_lower: return "health_policy"
        if "vehicle" in text_lower or "motor" in text_lower: return "motor_policy"
        return "general_policy"
    return "general"

def _get_base_structure(document_type):
    structures = {
        "contract": [
            "Executive Summary", "Parties and Roles", "Key Terms and Duration", 
            "Financial Obligations", "Rights and Responsibilities", "Usage Restrictions and Rules",
            "Termination Conditions", "Legal Clauses", "Practical Risks and Red Flags", 
            "What Should Be Negotiated or Checked Before Signing"
        ],
        "property": [
            "Executive Summary", "Parties and Property Details", "Ownership and Possession",
            "Financial Terms", "Key Obligations and Conditions", "Transfer Process and Timeline",
            "Restrictions and Encumbrances", "Legal Clauses", "Practical Risks and Red Flags",
            "What Should Be Verified Before Signing"
        ],
        "court_judgment": [
            "Facts", "Issues", "Reasoning", "Decision"
        ],
        "insurance": [
            "Executive Summary", "Policyholder and Insurer Details", "Coverage Details",
            "Premium and Payment Terms", "Exclusions and Limitations", "Claim Process and Documentation",
            "Waiting Periods and Conditions", "Legal Clauses", "Practical Risks and Red Flags",
            "What Should Be Clarified Before Purchase"
        ],
        "financial": [
            "Executive Summary", "Parties and Financial Product Details", "Key Terms and Conditions",
            "Financial Obligations", "Rights and Entitlements", "Fees, Charges, and Penalties",
            "Default and Consequences", "Legal Clauses", "Practical Risks and Red Flags",
            "What Should Be Understood Before Signing"
        ],
        "general": [
            "Executive Summary", "Parties Involved", "Key Terms and Conditions",
            "Financial Obligations", "Rights and Responsibilities", "Restrictions and Limitations",
            "Termination Conditions", "Legal Clauses", "Practical Risks and Red Flags",
            "What Should Be Reviewed Carefully"
        ]
    }
    return structures.get((document_type or "general").lower(), structures["general"])

def _normalize_heading_for_match(text: str) -> str:
    s = str(text or "").strip().lower()
    s = s.replace("*", "").replace("#", "")
    s = re.sub(r"^\s*(?:article|section|clause|schedule|annexure|appendix)\s+[\divx\.\-\)\(]+\s*[:\-]?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\s*(?:[\divx]+|[a-z])[\.\)]\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" :.-")
    return s

def _slugify_heading(text: str) -> str:
    s = _normalize_heading_for_match(text)
    s = re.sub(r"[^a-z0-9\s_]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "section"

def _is_noise_heading(line: str) -> bool:
    normalized = _normalize_heading_for_match(line)
    if not normalized:
        return True
    _NOISE_HEADINGS = {
        "designated account details", "repayment schedule", "execution",
        "signatures", "signature block", "witness", "witnesses",
        "in witness whereof", "signed and delivered", "general context",
        "schedule", "annexure", "appendix", "table of contents",
        "contents", "index", "page", "date", "place", "stamp duty",
        "registration", "notarization", "attestation", "declaration",
        "acknowledgement", "acknowledgment", "verification",
        "affidavit", "power of attorney", "poa", "enclosures",
        "list of documents", "disclaimer", "note", "notes",
        "exhibit", "exhibits", "format", "form", "proforma",
    }
    if normalized in _NOISE_HEADINGS:
        return True
    if re.match(r"^(mr|ms|mrs|dr)\.?\s+", normalized):
        return True
    if "name: ____" in line.lower() or "address: ____" in line.lower():
        return True
    # Single-word headings that are too generic
    if len(normalized.split()) == 1 and normalized not in {
        "definitions", "recitals", "preamble", "representations",
        "warranties", "covenants", "indemnification", "termination",
        "confidentiality", "arbitration", "jurisdiction", "miscellaneous",
        "default", "remedies", "insurance", "security", "guarantee",
        "collateral", "disbursement", "prepayment", "moratorium",
    }:
        return True
    return False

def extract_sections(text):
    MIN_SECTION_CONTENT_CHARS = 50  # Sections with less content are likely noise
    sections = []
    lines = text.split('\n')
    current_title = "General Context"
    current_content = []
    
    # Matches: Article 1, Section 2.1, Clause IV
    pattern1 = re.compile(r'^(?:Article|Section|Clause|Schedule|Annexure|Appendix)\s+[\dIVX\.\-]+', re.IGNORECASE)
    # Matches Main Headings: 1. Definitions, A. Representations, I. Background
    # Require at least 2 words after the number to avoid matching list items
    pattern2 = re.compile(r'^(?:[\dIVX]+|[A-Z])\s*[\.\)]\s+[A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+)*')
    
    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        
        is_heading = False
        if len(stripped) < 120:
            clean_line = stripped.replace('*', '').replace('#', '').strip()
            word_count = len(clean_line.split())
            
            if stripped.startswith('#'):
                is_heading = True
            elif stripped.startswith('**') and stripped.endswith('**') and 2 <= word_count < 12:
                is_heading = True
            elif pattern1.match(clean_line):
                is_heading = True
            elif pattern2.match(clean_line) and word_count >= 2 and word_count <= 10 and not clean_line.endswith(('.', ';', ',')):
                is_heading = True
            elif clean_line.isupper() and 2 <= word_count < 8:
                is_heading = True
                
        if is_heading:
            if _is_noise_heading(stripped):
                continue
            if current_content:
                sections.append({'title': current_title, 'content': '\n'.join(current_content)})
            current_title = stripped.replace('*', '').replace('#', '').strip()
            current_content = []
        else:
            current_content.append(line)
            
    if current_content:
        sections.append({'title': current_title, 'content': '\n'.join(current_content)})
    
    # Filter out noise: drop "General Context" placeholder and tiny sections
    filtered = []
    for s in sections:
        title = s['title'].strip()
        content = s['content'].strip()
        if title == "General Context":
            continue
        if len(content) < MIN_SECTION_CONTENT_CHARS:
            continue
        filtered.append(s)
    return filtered

def chunk_document_sequentially(text, max_words=3000):
    from app.services.ai.chunking import chunk_document
    return chunk_document(text, min_words=int(max_words*0.8), max_words=max_words, overlap_words=200)

def chunk_document_by_sections(text, max_words=3000):
    sections = extract_sections(text)
    if len(sections) < 3:
        return chunk_document_sequentially(text, max_words)
    chunks = []
    current_chunk = []
    current_words = 0
    for sec in sections:
        sec_text = f"{sec['title']}\n{sec['content']}"
        sec_words = count_words(sec_text)
        if sec_words > max_words:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_words = 0
            sub_chunks = chunk_document_sequentially(sec_text, max_words)
            chunks.extend(sub_chunks)
        else:
            if current_words + sec_words > max_words:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [sec_text]
                current_words = sec_words
            else:
                current_chunk.append(sec_text)
                current_words += sec_words
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    return chunks

def _sentences(text):
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned: return []
    normalized = re.sub(r"([.!?])\s+", r"\1\n", cleaned)
    return [piece.strip() for piece in normalized.splitlines() if piece.strip()]

def _sentence_score(sentence):
    lowered = sentence.lower()
    score = 0
    high_priority = ("shall", "must", "agrees", "obligation", "liable", "indemnify", "terminate", "default", "penalty", "payment", "rent")
    for keyword in high_priority:
        if keyword in lowered: score += 3
    if any(ch.isdigit() for ch in sentence): score += 2
    if re.search(r"\b(?:Section|Clause|Article)\s+\d+", sentence, re.IGNORECASE): score += 3
    if re.search(r"(?:Rs\.?|INR|₹|USD|\$)", sentence, re.IGNORECASE): score += 3
    return score

def _select_extractive_sentences(text, limit=8):
    sentences = list(dict.fromkeys(_sentences(text)))
    if not sentences: return []
    ranked = sorted(enumerate(sentences), key=lambda item: (-_sentence_score(item[1]), item[0]))
    chosen = sorted(index for index, _ in ranked[:limit])
    return [sentences[index] for index in chosen]

async def _generate_direct_summary(text, document_type, subtype, use_predefined_structure, selected_sections):
    if use_predefined_structure:
        structure = _get_base_structure(document_type)
        structure_prompt = "\n".join([f"- **{s}**" for s in structure])
        prompt = f"""You are a Legal Expert analyzing a {document_type} ({subtype}).
Provide a comprehensive summary of the document using EXACTLY these headings:
{structure_prompt}

Ensure all key facts, monetary values, and obligations are preserved.
For each heading, keep language simple and readable but legally accurate.
Do not skip headings; if a section has limited data, write "Not clearly specified in the document."
DOCUMENT TEXT:
{text}"""
    else:
        headings = "\n".join([f"- {s}" for s in selected_sections]) if selected_sections else ""
        prompt = f"""You are a Legal Expert summarizing selected sections of a {document_type} ({subtype}).
Summarize ONLY the selected sections below.
Keep the heading names exactly as provided in SELECTED HEADINGS.
Output sections in the EXACT ORDER listed below — do not reorder.
Under each heading, provide 2-6 concise bullet points.
Use simple language but preserve legal meaning and key legal terms.
Do not include sections outside this list.

SELECTED HEADINGS:
{headings}

DOCUMENT TEXT:
{text}"""
    
    return await gemini_client.generate(prompt)

async def _generate_chunk_summary(chunk, document_type, subtype, use_predefined_structure):
    prompt = f"""You are a Legal Expert analyzing a part of a {document_type} ({subtype}).
Extract the most important facts, obligations, financial figures, and clauses.
Be concise but do not lose critical legal details.
CHUNK TEXT:
{chunk}"""
    return await gemini_client.generate(prompt)

async def _merge_chunk_summaries(partials, document_type, subtype, use_predefined_structure, selected_sections):
    joined = "\n\n--- CHUNK ---\n\n".join(partials)
    if use_predefined_structure:
        structure = _get_base_structure(document_type)
        structure_prompt = "\n".join([f"- **{s}**" for s in structure])
        prompt = f"""You are a Legal Expert merging summaries of a {document_type} ({subtype}).
Merge the following chunked summaries into a single cohesive document summary using EXACTLY these headings:
{structure_prompt}

Do not repeat information unnecessarily.
CHUNK SUMMARIES:
{joined}"""
    else:
        headings = "\n".join([f"- {s}" for s in selected_sections]) if selected_sections else ""
        prompt = f"""You are a Legal Expert merging summaries of selected sections of a {document_type} ({subtype}).
Produce a final summary ONLY for these selected headings.
Keep heading names exactly as provided.
Output sections in the EXACT ORDER listed below — do not reorder.
Under each heading, provide concise bullet points with legally accurate wording.
Avoid duplication and keep output easy to read.
SELECTED HEADINGS:
{headings}
CHUNK SUMMARIES:
{joined}"""
    return await gemini_client.generate(prompt)

def _parse_markdown_to_structured(markdown, document_type):
    structured = {}
    current_section = "executive_summary"
    lines = markdown.split('\n')
    current_content = []
    
    structures = _get_base_structure(document_type)
    structure_map = {_normalize_heading_for_match(s): s for s in structures}
    ordered_keys = [s.lower().replace(" ", "_").replace(",", "") for s in structures]
    
    for line in lines:
        stripped = line.strip().replace('**', '')
        normalized = _normalize_heading_for_match(stripped)
        matched = None
        if normalized in structure_map:
            matched = normalized
        else:
            for key in structure_map.keys():
                if normalized.startswith(key) or key in normalized:
                    matched = key
                    break
        if matched:
            if current_content:
                structured[current_section] = "\n".join(current_content).strip()
            current_section = structure_map[matched].lower().replace(' ', '_').replace(',', '')
            current_content = []
        else:
            current_content.append(line)
            
    if current_content:
        structured[current_section] = "\n".join(current_content).strip()
    # Preserve canonical order and drop empty sections.
    ordered_structured = {}
    for key in ordered_keys:
        val = structured.get(key)
        if isinstance(val, str) and val.strip():
            ordered_structured[key] = val.strip()
    for key, val in structured.items():
        if key not in ordered_structured and isinstance(val, str) and val.strip():
            ordered_structured[key] = val.strip()
    return ordered_structured

def _parse_selected_markdown_to_structured(markdown: str, selected_sections: list[str]) -> dict:
    if not selected_sections:
        return {}
    section_map = {_normalize_heading_for_match(s): s for s in selected_sections}
    ordered_keys = [_slugify_heading(s) for s in selected_sections]
    structured = {}
    current_key = ordered_keys[0] if ordered_keys else "section"
    current_content = []
    lines = str(markdown or "").split("\n")

    for line in lines:
        stripped = line.strip().replace("**", "")
        normalized = _normalize_heading_for_match(stripped)
        matched_original = section_map.get(normalized)
        if not matched_original:
            for key_norm, original in section_map.items():
                if normalized.startswith(key_norm) or key_norm in normalized:
                    matched_original = original
                    break
        if matched_original:
            if current_content:
                structured[current_key] = "\n".join(current_content).strip()
            current_key = _slugify_heading(matched_original)
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        structured[current_key] = "\n".join(current_content).strip()

    ordered_structured = {}
    for key in ordered_keys:
        val = structured.get(key)
        if isinstance(val, str) and val.strip():
            ordered_structured[key] = val.strip()
    for key, val in structured.items():
        if key not in ordered_structured and isinstance(val, str) and val.strip():
            ordered_structured[key] = val.strip()
    return ordered_structured

async def build_hybrid_summary(cleaned_text, document_type, page_count=None, selected_sections=None, checklist_mode=None):
    text = str(cleaned_text or "").strip()
    subtype = _detect_subtype(text, document_type)
    
    if not text:
        return SummaryResult("direct", 0, [], [], "", "", [], {})

    if checklist_mode == "selected" and selected_sections:
        sections = extract_sections(text)
        # Normalize both sides for fuzzy matching to prevent section skipping
        selected_normalized = {_normalize_heading_for_match(s): s for s in selected_sections}
        matched_sections = []
        for sec in sections:
            sec_norm = _normalize_heading_for_match(sec['title'])
            # Check exact match first, then substring containment
            if sec_norm in selected_normalized:
                matched_sections.append(sec)
            else:
                for sel_norm in selected_normalized:
                    if sec_norm == sel_norm or sel_norm in sec_norm or sec_norm in sel_norm:
                        matched_sections.append(sec)
                        break
        filtered_text = "\n\n".join([f"{s['title']}\n{s['content']}" for s in matched_sections])
        if not filtered_text.strip():
            filtered_text = text 
        text_to_process = filtered_text
        use_predefined_structure = False
    else:
        text_to_process = text
        use_predefined_structure = True
        
    words = count_words(text_to_process)
    
    if words <= 8000:
        route = "direct"
        chunks = [text_to_process]
        try:
            final_summary = await _generate_direct_summary(text_to_process, document_type, subtype, use_predefined_structure, selected_sections)
        except Exception:
            final_summary = "Summary generation failed."
        partial_summaries = []
    else:
        route = "chunked"
        if document_type == "court_judgment":
            chunks = chunk_document_sequentially(text_to_process, 3000)
        else:
            chunks = chunk_document_by_sections(text_to_process, 3000)
            
        partial_summaries = []
        for chunk in chunks:
            try:
                chunk_sum = await _generate_chunk_summary(chunk, document_type, subtype, use_predefined_structure)
                partial_summaries.append(chunk_sum)
            except Exception:
                pass
            
        try:
            final_summary = await _merge_chunk_summaries(partial_summaries, document_type, subtype, use_predefined_structure, selected_sections)
        except Exception:
            final_summary = "Summary merging failed."
        
    extractive_sentences = _select_extractive_sentences(text, limit=10)
    extractive_summary = "\n".join([f"- {s}" for s in extractive_sentences])
    
    structured = {}
    if use_predefined_structure:
        structured = _parse_markdown_to_structured(final_summary, document_type)
    else:
        structured = _parse_selected_markdown_to_structured(final_summary, selected_sections or [])
        
    return SummaryResult(route, words, chunks, partial_summaries, final_summary, extractive_summary, extractive_sentences, structured)