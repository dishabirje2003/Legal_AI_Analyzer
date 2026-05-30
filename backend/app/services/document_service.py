from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.services.supabase_service import supabase, supabase_execute

logger = logging.getLogger(__name__)


class DocumentService:
    def insert_document(
        self,
        *,
        document_id: str,
        user_id: str | None,
        document_name: str,
        document_type: str,
        file_url: str,
        processing_status: str,
    ) -> dict:
        payload: dict = {
            "id": document_id,
            "document_name": document_name,
            "document_type": document_type,
            "file_url": file_url,
            "processing_status": processing_status,
            "upload_date": datetime.utcnow().isoformat(),
        }
        if user_id:
            payload["user_id"] = user_id

        # Some DBs will reject explicitly setting upload_date if column has default.
        # Try with upload_date first, then retry without it.
        try:
            return supabase_execute(supabase.table("documents").insert(payload)).data[0]
        except Exception:
            payload.pop("upload_date", None)
            return supabase_execute(supabase.table("documents").insert(payload)).data[0]

    def list_documents(self, *, user_id: str | None = None, limit: int = 200) -> list[dict]:
        q = supabase.table("documents").select(
            "id, document_name, document_type, upload_date, processing_status, file_url"
        ).order("upload_date", desc=True).limit(limit)
        if user_id:
            q = q.eq("user_id", user_id)
        return supabase_execute(q).data

    def get_document(self, *, document_id: str) -> dict | None:
        rows = supabase_execute(
            supabase.table("documents")
            .select("id, document_name, document_type, upload_date, processing_status, file_url, user_id")
            .eq("id", document_id)
            .limit(1)
        ).data
        return rows[0] if rows else None

    def _fetch_latest_document_text_row(self, document_id: str) -> dict | None:
        """Best-effort: tolerate missing `created_at` or RLS quirks."""
        base = lambda: supabase.table("document_text").select("extracted_text").eq("document_id", document_id)
        for wrap in (
            lambda b: b.order("created_at", desc=True).limit(1),
            lambda b: b.order("id", desc=True).limit(1),
            lambda b: b.limit(1),
        ):
            try:
                rows = supabase_execute(wrap(base())).data
                if rows:
                    return rows[0]
            except Exception:
                continue
        return None

    def get_extracted_text(self, *, document_id: str) -> dict | None:
        """
        Prefer document_text.extracted_text; fall back to legacy analysis_results or empty.
        Returns: { extracted_text, extraction_method? }
        """
        try:
            row = self._fetch_latest_document_text_row(document_id)
            if row and row.get("extracted_text") is not None:
                t = row.get("extracted_text")
                return {
                    "extracted_text": t if isinstance(t, str) else str(t),
                    "extraction_method": None,
                }
        except Exception:
            pass

        try:
            base = lambda: (
                supabase.table("analysis_results")
                .select("extracted_text, extraction_method")
                .eq("document_id", document_id)
            )
            rows = None
            for wrap in (
                lambda b: b.order("created_at", desc=True).limit(1),
                lambda b: b.order("id", desc=True).limit(1),
                lambda b: b.limit(1),
            ):
                try:
                    rows = supabase_execute(wrap(base())).data
                    if rows:
                        break
                except Exception:
                    continue
            if rows:
                t = rows[0].get("extracted_text")
                return {
                    "extracted_text": (t if isinstance(t, str) else str(t)) if t is not None else "",
                    "extraction_method": rows[0].get("extraction_method") or None,
                }
        except Exception:
            return None
        return None

    def save_document_text(
        self,
        *,
        document_id: str,
        extracted_text: str,
        page_count: int | None,
    ) -> None:
        supabase_execute(supabase.table("document_text").delete().eq("document_id", document_id))
        payload: dict = {
            "id": str(uuid4()),
            "document_id": document_id,
            "extracted_text": extracted_text,
        }
        if page_count is not None:
            payload["page_count"] = page_count
        try:
            supabase_execute(supabase.table("document_text").insert(payload))
        except Exception:
            payload.pop("page_count", None)
            supabase_execute(supabase.table("document_text").insert(payload))

    def get_page_count(self, *, document_id: str) -> int | None:
        try:
            q = supabase.table("document_text").select("page_count").eq("document_id", document_id)
            rows = None
            try:
                rows = supabase_execute(q.order("created_at", desc=True).limit(1)).data
            except Exception:
                try:
                    rows = supabase_execute(q.order("id", desc=True).limit(1)).data
                except Exception:
                    rows = supabase_execute(q.limit(1)).data
            if rows and rows[0].get("page_count") is not None:
                return int(rows[0]["page_count"])
        except Exception:
            return None
        return None

    def get_analysis(self, *, document_id: str) -> dict | None:
        select_variants = (
            "extractive_summary, abstractive_summary, entities",
            "extractive_summary, abstractive_summary",
        )
        for select_cols in select_variants:
            try:
                base = lambda sc=select_cols: (
                    supabase.table("analysis_results")
                    .select(sc)
                    .eq("document_id", document_id)
                )
                for wrap in (
                    lambda b: b.order("created_at", desc=True).limit(1),
                    lambda b: b.order("id", desc=True).limit(1),
                    lambda b: b.limit(1),
                ):
                    try:
                        rows = supabase_execute(wrap(base())).data
                        if rows:
                            return rows[0]
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    def delete_document_cascade(self, *, document_id: str) -> bool:
        """
        Remove DB rows (analysis_results, document_chunks, document_text, documents),
        Supabase Storage file, Pinecone vectors, and local tmp extracted-text files.
        """
        from app.services.ai.pinecone_store import delete_vector_ids
        from app.services.storage_service import storage_service

        doc = self.get_document(document_id=document_id)
        if not doc:
            return False

        file_url = (doc.get("file_url") or "").strip()

        vector_ids: list[str] = []
        try:
            resp = supabase_execute(
                supabase.table("document_chunks")
                .select("pinecone_vector_id")
                .eq("document_id", document_id)
            )
            for row in resp.data or []:
                vid = row.get("pinecone_vector_id")
                if isinstance(vid, str) and vid.strip():
                    vector_ids.append(vid.strip())
        except Exception as e:
            logger.warning("Could not list chunk vector ids for %s: %s", document_id, e)

        for table in ("analysis_results", "document_chunks", "document_text"):
            try:
                supabase_execute(supabase.table(table).delete().eq("document_id", document_id))
            except Exception as e:
                logger.warning("delete from %s failed for %s: %s", table, document_id, e)

        supabase_execute(supabase.table("documents").delete().eq("id", document_id))

        if vector_ids:
            try:
                delete_vector_ids(vector_ids)
            except Exception as e:
                logger.warning("Pinecone delete failed for %s: %s", document_id, e)

        if file_url:
            storage_service.delete_file_by_public_url(file_url)

        for base in (
            Path(__file__).resolve().parents[1] / "tmp",
            Path(__file__).resolve().parents[2] / "tmp",
        ):
            p = base / f"{document_id}.txt"
            if p.is_file():
                try:
                    p.unlink()
                except OSError:
                    pass

        return True


document_service = DocumentService()

