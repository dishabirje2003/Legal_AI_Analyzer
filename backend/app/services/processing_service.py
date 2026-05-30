from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.services.document_service import document_service
from app.services.ocr_service import ocr_service
from app.services.supabase_service import supabase, supabase_execute

logger = logging.getLogger(__name__)

class ProcessingService:
    def process_document(self, document_id):
        doc_rows = supabase_execute(supabase.table("documents").select("id, user_id, document_name, document_type, file_url, processing_status").eq("id", document_id)).data
        if not doc_rows:
            logger.warning("Document %s not found for processing", document_id)
            return False
        doc = doc_rows[0]
        file_url = doc.get("file_url")
        if not file_url:
            supabase_execute(supabase.table("documents").update({"processing_status": "failed"}).eq("id", document_id))
            return False
        supabase_execute(supabase.table("documents").update({"processing_status": "processing"}).eq("id", document_id))
        try:
            with httpx.Client(timeout=120) as client:
                response = client.get(file_url)
                response.raise_for_status()
                file_bytes = response.content
            extracted = ocr_service.extract_text(filename=doc.get("document_name") or "document.pdf", content=file_bytes)
            try:
                document_service.save_document_text(document_id=document_id, extracted_text=extracted.text, page_count=extracted.page_count)
            except Exception as exc:
                logger.exception("document_text save failed: %s", exc)
                tmp_dir = Path(__file__).resolve().parents[1] / "tmp"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                (tmp_dir / f"{document_id}.txt").write_text(extracted.text, encoding="utf-8")
            supabase_execute(supabase.table("documents").update({"processing_status": "extracted"}).eq("id", document_id))
            try:
                from app.services.ai.pipeline import ai_pipeline

                ai_pipeline.analyze_document(document_id)
                supabase_execute(supabase.table("documents").update({"processing_status": "analyzed"}).eq("id", document_id))
                return True
            except Exception as exc:
                logger.exception("AI pipeline failed for %s: %s", document_id, exc)
                supabase_execute(supabase.table("documents").update({"processing_status": "extracted"}).eq("id", document_id))
                return False
        except Exception:
            logger.exception("Extraction or download failed for %s", document_id)
            supabase_execute(supabase.table("documents").update({"processing_status": "failed"}).eq("id", document_id))
            return False

    def process_property_agreement(self, document_id):
        return None

    def process_rental_contract(self, document_id):
        return None

    def process_employment_contract(self, document_id):
        return None

    def process_court_judgment(self, document_id):
        return None

processing_service = ProcessingService()
