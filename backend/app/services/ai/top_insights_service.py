import logging
import json
import re
import time
from typing import List, Dict, Any
import httpx

from app.services.supabase_service import supabase, supabase_execute
from app.config import settings

logger = logging.getLogger(__name__)

def generate_top_insights(text: str, document_type: str, document_id: str = None) -> List[Dict[str, str]]:
    if not text:
        return []

    if not settings.gemini_api_key:
        logger.warning("Gemini API key is missing - top insights generation disabled")
        return []

    prompt = f"""You are a senior legal analyst AI.

Your task is to extract ONLY REAL, DOCUMENT-SPECIFIC Top Insights from the provided legal document.

STRICT INSTRUCTIONS:

1. DO NOT generate generic, template, or assumed insights.
   - Avoid generic phrases like "The document outlines the obligations of the parties" or "This is a standard agreement."

2. Every insight MUST:
   - Be directly grounded in the document text
   - Highlight a specific, highly important fact, ruling, obligation, or monetary value
   - Not be a risk or warning (Do not use words like 'liability', 'exposure', 'risk', 'danger')

3. If the document does NOT contain meaningful insights (e.g., it is too short or incomplete):
   - Return an empty list []
   - DO NOT hallucinate or infer insights

4. Be precise and factual:
   - Use actual names, dates, amounts, and specific terms mentioned in the text.
   - Example: "Defendant Orion Data Systems must pay ₹15,00,000 by July 15th." (Good)
   - Example: "The defendant must pay the compensation amount." (Bad - too generic)

5. Output MUST be valid JSON only (no markdown, no explanation)

OUTPUT FORMAT:

[
  {{
    "title": "Short insight title",
    "description": "Clear, factual explanation tied to document content",
    "supporting_text": "Exact or paraphrased supporting clause from the text"
  }}
]

DOCUMENT TEXT:
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
                with httpx.Client(timeout=90.0) as client:
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
                    
                    # Clean markdown formatting if present
                    llm_text = re.sub(r"^```(?:json)?\s*", "", llm_text.strip())
                    llm_text = re.sub(r"\s*```\s*$", "", llm_text)
                    
                    try:
                        insights = json.loads(llm_text)
                    except json.JSONDecodeError as e:
                        raise Exception("Invalid LLM JSON output") from e
                        
                    if not isinstance(insights, list):
                        raise Exception("Invalid LLM JSON output - expected array")
                        
                    # Filter and structure insights
                    mapped_insights = []
                    for i, ins in enumerate(insights):
                        mapped_insights.append({
                            "id": f"insight-{i+1}",
                            "title": str(ins.get("title", "")),
                            "description": str(ins.get("description", "")),
                            "supporting_text": str(ins.get("supporting_text", ""))
                        })
                        
                    return mapped_insights

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
                    logger.warning(f"Insights LLM {model} failed: {e}")
                    break
            except Exception as e:
                logger.warning(f"Insights LLM {model} failed: {e}")
                break
            
    logger.error("All LLM models failed for top insights generation")
    return []
