import logging
import json
import re
import time
from typing import List, Dict, Any
from uuid import uuid4
import httpx

from app.services.supabase_service import supabase, supabase_execute
from app.services.supabase_service import supabase, supabase_execute
from app.config import settings

logger = logging.getLogger(__name__)

def _generate_risks_with_llm(text: str, document_type: str, document_id: str = None) -> List[Dict[str, Any]]:
    if not text:
        raise Exception("Document text is empty - risk detection failed")
        
    if not settings.gemini_api_key:
        raise Exception("Gemini API key is missing - risk detection failed")

    prompt = f"""You are a senior legal risk analyst AI.

Your task is to extract ONLY REAL, DOCUMENT-SPECIFIC legal risks from the provided legal document.

STRICT INSTRUCTIONS:

1. DO NOT generate generic or template risks.
   - Avoid phrases like "Unlimited Liability Exposure", "Termination Risk", etc. unless they are clearly supported by the document.

2. Every risk MUST:
   - Be directly grounded in the document text
   - Reference a specific clause, section, or factual situation
   - Include a short explanation of WHY it is a risk

3. If the document does NOT contain meaningful risks:
   - Return an empty list []
   - DO NOT hallucinate or infer risks

4. Be precise and conservative:
   - Prefer missing a risk over inventing one

5. Output MUST be valid JSON only (no markdown, no explanation)

OUTPUT FORMAT:

[
  {{
    "title": "Short risk title",
    "description": "Clear explanation tied to document content",
    "severity": "low | medium | high",
    "clause_reference": "Clause number or section if available"
  }}
]

DOCUMENT:
{text}
"""

    MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        settings.gemini_model_name
    ]

    for model in MODELS:
        for attempt in range(3):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1}
                }
                with httpx.Client(timeout=120.0) as client:
                    res = client.post(url, params={"key": settings.gemini_api_key}, json=body)
                    
                    if res.status_code == 429:
                        sleep_time = (2 ** attempt) * 5
                        logger.warning(f"Rate limit for {model}, retrying in {sleep_time}s")
                        if document_id:
                            try:
                                supabase_execute(supabase.table("documents").update({"processing_status": f"High AI Load. Retrying in {sleep_time}s..."}).eq("id", document_id))
                            except Exception:
                                pass
                        time.sleep(sleep_time)
                        if document_id:
                            try:
                                supabase_execute(supabase.table("documents").update({"processing_status": "processing"}).eq("id", document_id))
                            except Exception:
                                pass
                        continue
                        
                    res.raise_for_status()
                    data = res.json()
                    
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise Exception("No candidates returned by LLM")
                    
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        raise Exception("No parts in LLM response")
                        
                    llm_text = parts[0].get("text", "")
                    
                    print("DOCUMENT TYPE:", document_type)
                    print("LLM RAW OUTPUT:", llm_text)
                    
                    llm_text = re.sub(r"^```(?:json)?\s*", "", llm_text.strip())
                    llm_text = re.sub(r"\s*```\s*$", "", llm_text)
                    
                    try:
                        risks = json.loads(llm_text)
                    except json.JSONDecodeError as e:
                        raise Exception("Invalid LLM JSON output") from e
                        
                    if not isinstance(risks, list):
                        raise Exception("Invalid LLM JSON output - expected array")
                        
                    print("PARSED RISKS:", risks)
                    print("FINAL RISKS SOURCE: LLM")
                    
                    mapped_risks = []
                    for idx, r in enumerate(risks):
                        title = str(r.get("title", ""))
                        if not title:
                            continue
                            
                        sev = str(r.get("severity", "medium")).lower()
                        if sev not in ["low", "medium", "high"]:
                            sev = "medium"
                            
                        desc = str(r.get("description", ""))
                        clause_ref = str(r.get("clause_reference", ""))
                        
                        mapped_risks.append({
                            "clause_id": f"llm-risk-{idx}",
                            "title": title,
                            "risk_type": document_type,
                            "severity": sev,
                            "party": "Not specified",
                            "affected_party": "Not specified",
                            "counterparty": "Counterparty",
                            "category": "Risk",
                            "tags": ["Risk"],
                            "explanation": desc,
                            "legal_reason": desc,
                            "clause_text": clause_ref,
                            "source_clause_texts": [clause_ref] if clause_ref else [],
                        })
                        
                    return mapped_risks

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    sleep_time = (2 ** attempt) * 5
                    logger.warning(f"Rate limit for {model}, retrying in {sleep_time}s")
                    if document_id:
                        try:
                            supabase_execute(supabase.table("documents").update({"processing_status": f"High AI Load. Retrying in {sleep_time}s..."}).eq("id", document_id))
                        except Exception:
                            pass
                    time.sleep(sleep_time)
                    if document_id:
                        try:
                            supabase_execute(supabase.table("documents").update({"processing_status": "processing"}).eq("id", document_id))
                        except Exception:
                            pass
                    continue
                else:
                    logger.warning(f"{model} failed: {e}")
                    break
            except Exception as e:
                logger.warning(f"{model} failed: {e}")
                break
                
    raise Exception("All LLM models failed for risk detection")

def detect_risks(
    clauses: List[Dict[str, Any]],
    entities: Dict[str, Any],
    text: str,
    structured_summary: Dict[str, Any] | None = None,
    document_type: str | None = None,
    document_id: str = None,
) -> Dict[str, Any]:
    
    try:
        llm_risks = _generate_risks_with_llm(text, document_type or "general", document_id)
        
        MAX_BY_SEVERITY = {"high": 5, "medium": 5, "low": 3}
        high_risks = [r for r in llm_risks if r["severity"] == "high"][: MAX_BY_SEVERITY["high"]]
        medium_risks = [r for r in llm_risks if r["severity"] == "medium"][: MAX_BY_SEVERITY["medium"]]
        low_risks = [r for r in llm_risks if r["severity"] == "low"][: MAX_BY_SEVERITY["low"]]

        kept_count = len(high_risks) + len(medium_risks) + len(low_risks)
        risk_score = max(0, 100 - (len(high_risks) * 18 + len(medium_risks) * 10 + len(low_risks) * 4))
        
        if high_risks or risk_score < 45:
            risk_level = "High"
        elif medium_risks or risk_score < 75:
            risk_level = "Medium"
        else:
            risk_level = "Low"
            
        doc_cat = document_type or "general"

        return {
            "summary": {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "contract_type": doc_cat,
                "detected_patterns": len(llm_risks),
                "published_risks": kept_count,
            },
            "high_risks": high_risks,
            "medium_risks": medium_risks,
            "low_risks": low_risks,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"LLM risk detection failed: {e}")
        return {
            "status": "failed",
            "reason": str(e),
            "risks": [],
            "summary": {"risk_score": 100, "risk_level": "Low", "contract_type": document_type or "general", "detected_patterns": 0, "published_risks": 0},
            "high_risks": [],
            "medium_risks": [],
            "low_risks": []
        }

def process_and_store_risks(
    document_id: str,
    clauses: List[Dict[str, Any]],
    entities: Dict[str, Any],
    text: str,
    structured_summary: Dict[str, Any] | None = None,
    document_type: str | None = None,
) -> Dict[str, Any]:
    enhanced_risks = detect_risks(
        clauses=clauses,
        entities=entities,
        text=text,
        structured_summary=structured_summary,
        document_type=document_type,
        document_id=document_id,
    )
    
    if enhanced_risks.get("status") == "failed" or not (enhanced_risks.get("high_risks") or enhanced_risks.get("medium_risks") or enhanced_risks.get("low_risks")):
        logger.error("No risks generated or risk generation failed - skipping save")
        return enhanced_risks
    
    payload = {
        "id": str(uuid4()),
        "document_id": document_id,
        "risks": enhanced_risks
    }
    
    try:
        supabase_execute(supabase.table("document_risks").delete().eq("document_id", document_id))
    except Exception as exc:
        logger.warning("Failed to delete old risks for %s: %s", document_id, exc)
    
    try:
        supabase_execute(supabase.table("document_risks").insert(payload))
    except Exception as exc:
        logger.error("Failed to store document risks for %s: %s", document_id, exc)
        
    return enhanced_risks
