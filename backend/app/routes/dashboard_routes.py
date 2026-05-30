from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Query

from app.services.supabase_service import supabase, supabase_execute

router = APIRouter(tags=["dashboard"])


def _normalize_text(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", str(value or "").lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _semantic_signature(risk: dict[str, Any]) -> str:
    title = _normalize_text(risk.get("title") or risk.get("risk_type") or "")
    category = _normalize_text(risk.get("category") or "")
    risk_type = _normalize_text(risk.get("risk_type") or "")
    explanation = _normalize_text(risk.get("explanation") or "")
    explanation_tokens = " ".join(explanation.split()[:8])
    return "|".join([title, category, risk_type, explanation_tokens]).strip("|")


def _extract_final_risks(blob: Any) -> list[dict[str, Any]]:
    if isinstance(blob, list):
        return [r for r in blob if isinstance(r, dict)]
    if not isinstance(blob, dict):
        return []
    merged: list[dict[str, Any]] = []
    for key in ("high_risks", "medium_risks", "low_risks"):
        risks = blob.get(key)
        if isinstance(risks, list):
            merged.extend([r for r in risks if isinstance(r, dict)])
    return merged


@router.get("/dashboard/risk-summary")
def get_dashboard_risk_summary(
    user_id: str | None = Query(default=None, description="Current user id"),
):
    # Restrict aggregation to finalized analysis statuses.
    # Current pipeline writes "analyzed" on success (not always "completed").
    q = supabase.table("documents").select("id, processing_status").limit(2000)
    if user_id:
        q = q.eq("user_id", user_id)
    docs = supabase_execute(q).data or []
    finalized_statuses = {"completed", "analyzed", "processed"}
    docs = [
        d for d in docs
        if str(d.get("processing_status") or "").strip().lower() in finalized_statuses
    ]
    if not docs:
        return {
            "total_risks": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
        }

    doc_ids = [d.get("id") for d in docs if d.get("id")]
    if not doc_ids:
        return {
            "total_risks": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
        }

    risk_rows = (
        supabase_execute(
            supabase.table("document_risks")
            .select("document_id, risks")
            .in_("document_id", doc_ids)
            .limit(5000)
        ).data
        or []
    )

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in risk_rows:
        for risk in _extract_final_risks(row.get("risks")):
            sig = _semantic_signature(risk)
            if not sig or sig in seen:
                continue
            seen.add(sig)
            deduped.append(risk)

    high = sum(1 for r in deduped if str(r.get("severity", "")).lower() == "high")
    medium = sum(1 for r in deduped if str(r.get("severity", "")).lower() == "medium")
    low = sum(1 for r in deduped if str(r.get("severity", "")).lower() == "low")

    return {
        "total_risks": len(deduped),
        "high_risk_count": high,
        "medium_risk_count": medium,
        "low_risk_count": low,
    }

