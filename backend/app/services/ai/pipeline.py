from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path as FilePath
from uuid import uuid4

from app.services.ai.legal_summarization import build_hybrid_summary
from app.services.ai.ner import extract_entities
from app.services.ai.text_cleaning import clean_text
from app.services.document_service import document_service
from app.services.supabase_service import supabase, supabase_execute

logger = logging.getLogger(__name__)

# Fix 1: Known document types accepted by legal_summarization prompts.
# Anything else (e.g. 'general_legal_document') maps to 'general'.
_KNOWN_DOC_TYPES = {'contract', 'property', 'court_judgment', 'insurance', 'financial', 'general'}


def _normalize_document_type(raw_type: str | None) -> str:
    """Map raw document_type values to types understood by the summarization engine."""
    t = str(raw_type or '').strip().lower()
    if t in _KNOWN_DOC_TYPES:
        return t
    
    # Map the combined frontend type
    if t == 'insurance/financial':
        return 'insurance'
        
    # Common aliases
    if t in ('rental', 'lease', 'employment', 'service', 'general_contract'):
        return 'contract'
    if t in ('sale_deed', 'property_agreement', 'agreement_to_sell'):
        return 'property'
    if t in ('judgment', 'court_order', 'petition', 'appeal'):
        return 'court_judgment'
    if t in ('policy', 'health_policy', 'motor_policy'):
        return 'insurance'
    if t in ('loan', 'financial_agreement'):
        return 'financial'
    
    # general_legal_document and everything else defaults to general
    return 'general'


def _run_async(coro):
    """Fix 2: Run an async coroutine safely regardless of whether an event loop is already running."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an existing event loop (e.g. FastAPI/uvicorn).
            # Use nest_asyncio if available, otherwise create a new thread.
            try:
                import nest_asyncio
                nest_asyncio.apply(loop)
                return loop.run_until_complete(coro)
            except ImportError:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # Fallback: always safe
        return asyncio.run(coro)

class AIPipeline:
    def _load_extracted_text(self, document_id):
        rows = supabase_execute(supabase.table("document_text").select("extracted_text").eq("document_id", document_id).limit(1)).data
        if rows and (rows[0].get("extracted_text") or "").strip():
            return rows[0].get("extracted_text") or ""
        for base in (FilePath(__file__).resolve().parents[1] / "tmp", FilePath(__file__).resolve().parents[2] / "tmp"):
            path = base / (str(document_id) + ".txt")
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        return ""

    def _save_chunks(self, document_id, chunks):
        try:
            supabase_execute(supabase.table("document_chunks").delete().eq("document_id", document_id))
        except Exception as exc:
            logger.warning("Chunk cleanup failed for %s: %s", document_id, exc)
        for index, chunk in enumerate(chunks):
            payloads = [
                {"id": str(uuid4()), "document_id": document_id, "chunk_index": index, "chunk_text": chunk},
                {"document_id": document_id, "chunk_index": index, "chunk_text": chunk},
                {"document_id": document_id, "chunk_order": index, "chunk_text": chunk},
                {"document_id": document_id, "chunk_index": index, "content": chunk},
            ]
            saved = False
            for payload in payloads:
                try:
                    supabase_execute(supabase.table("document_chunks").insert(payload))
                    saved = True
                    break
                except Exception:
                    continue
            if not saved:
                # Fix 3: log the failure but continue saving remaining chunks
                # (old code used `break` which silently dropped all subsequent chunks)
                logger.warning("Chunk save failed for %s at index %s — skipping this chunk", document_id, index)

    def _save_results(self, document_id, result, entities, grouped, cleaned_text):
        analysis_payload = {
            "raw": entities,
            "grouped": grouped,
            "top_insights": grouped.get("top_insights") if isinstance(grouped, dict) else None,
            "structured_summary": result.structured_summary,
            "extractive_sentences": result.extractive_sentences,
            "summary_route": result.route,
            "cleaned_word_count": result.word_count,
            "chunk_count": len(result.chunks) if result.chunks else 1,
            "partial_summaries": result.partial_summaries,
            "cleaned_text": cleaned_text,
        }
        payload = {
            "id": str(uuid4()),
            "document_id": document_id,
            "extractive_summary": result.extractive_summary,
            "abstractive_summary": result.final_summary,
            "entities": analysis_payload,
        }
        supabase_execute(supabase.table("analysis_results").delete().eq("document_id", document_id))
        try:
            supabase_execute(supabase.table("analysis_results").insert(payload))
        except Exception:
            payload.pop("id", None)
            supabase_execute(supabase.table("analysis_results").insert(payload))

    def analyze_document(self, document_id):
        raw_text = self._load_extracted_text(document_id)
        if not raw_text:
            logger.warning("No extracted text for %s", document_id)
            return None
        cleaned_text = clean_text(raw_text, for_summarization=True)
        if not cleaned_text:
            logger.warning("Cleaned text empty for %s", document_id)
            return None
        document = document_service.get_document(document_id=document_id) or {}
        page_count = document_service.get_page_count(document_id=document_id)
        raw_type = document.get("document_type") or "general"
        document_type = _normalize_document_type(raw_type)

        # Parallelize: Summarization (I/O bound) and Entity/Clause/Risk (CPU/I/O mixed)
        async def run_parallel_pipelines():
            # Task 1: Summarization
            summary_task = asyncio.create_task(build_hybrid_summary(cleaned_text, document_type, page_count=page_count))

            # Task 2: Entity, Clause, and Risk extraction (run CPU-heavy NER in thread)
            async def run_analysis_pipeline():
                # The upgraded extract_entities now returns the structured/grouped JSON directly
                grouped = await asyncio.to_thread(extract_entities, cleaned_text, document_type)
                
                # For backward compatibility with storage that expects a 'raw' list of {text, label}
                # we can synthesize a simple list if needed, or just use the grouped keys.
                # However, the pipeline stores 'grouped' as the primary structured data.
                entities = grouped 
                
                from app.services.ai.clause_detection_service import process_and_store_clauses
                detected_clauses = await asyncio.to_thread(process_and_store_clauses, document_id, cleaned_text, grouped)

                from app.services.ai.rag_service import store_clauses_in_pinecone
                await asyncio.to_thread(store_clauses_in_pinecone, document_id, detected_clauses)
                
                from app.services.ai.top_insights_service import generate_top_insights
                top_insights = await asyncio.to_thread(generate_top_insights, cleaned_text, document_type)

                return entities, grouped, detected_clauses, top_insights

            analysis_task = asyncio.create_task(run_analysis_pipeline())
            
            result, (entities, grouped, detected_clauses, top_insights) = await asyncio.gather(summary_task, analysis_task)
            
            return result, entities, grouped, detected_clauses, top_insights

        # Run the parallel pipeline
        result, entities, grouped, detected_clauses, top_insights = _run_async(run_parallel_pipelines())

        # Generate risks with the final structured summary for synthesis-quality outputs.
        from app.services.ai.risk_detection_service import process_and_store_risks
        _run_async(
            asyncio.to_thread(
                process_and_store_risks,
                document_id,
                detected_clauses,
                grouped,
                cleaned_text,
                result.structured_summary,
                document_type,
            )
        )
        
        stored_chunks = result.chunks if result.chunks else [cleaned_text]
        self._save_chunks(document_id, stored_chunks)
        # Keep top insights outside structured_summary to avoid polluting summary sections.
        if not isinstance(grouped, dict):
            grouped = {}
        grouped["top_insights"] = top_insights
        self._save_results(document_id, result, entities, grouped, cleaned_text)
        logger.info("AI pipeline completed for %s via %s (doc_type=%s)", document_id, result.route, document_type)
        return result

    def re_summarize_document(self, document_id, selected_sections=None, checklist_mode=None):
        raw_text = self._load_extracted_text(document_id)
        if not raw_text: return None
        cleaned_text = clean_text(raw_text, for_summarization=True)
        if not cleaned_text: return None
        
        document = document_service.get_document(document_id=document_id) or {}
        page_count = document_service.get_page_count(document_id=document_id)
        document_type = _normalize_document_type(document.get("document_type"))
        
        async def run_summary():
            return await build_hybrid_summary(
                cleaned_text, document_type, page_count=page_count, 
                selected_sections=selected_sections, checklist_mode=checklist_mode
            )
            
        result = _run_async(run_summary())
        
        # Load existing analysis to keep other fields intact
        from app.services.supabase_service import supabase_execute, supabase
        row = supabase_execute(supabase.table("analysis_results").select("entities").eq("document_id", document_id).limit(1)).data
        entities = {}
        grouped = {}
        if row and row[0].get("entities"):
            analysis_payload = row[0]["entities"]
            entities = analysis_payload.get("raw", {})
            grouped = analysis_payload.get("grouped", {})
            
        self._save_results(document_id, result, entities, grouped, cleaned_text)
        return result

ai_pipeline = AIPipeline()

class LegalDocumentPipeline:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def process_text(self, document_text, document_type="general", page_count=None):
        cleaned_text = clean_text(document_text, for_summarization=True)
        normalized_type = _normalize_document_type(document_type)
        result = _run_async(build_hybrid_summary(cleaned_text, normalized_type, page_count=page_count))
        return {
            "extractive_summary": result.extractive_summary,
            "readable_summary": result.final_summary,
            "structured_summary": result.structured_summary,
            "chunk_summaries": result.partial_summaries,
            "chunks": result.chunks,
            "route": result.route,
            "cleaned_text": cleaned_text,
        }
