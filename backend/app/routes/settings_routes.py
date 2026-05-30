from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.document_service import document_service
from app.services.supabase_service import supabase, supabase_execute

router = APIRouter(tags=["settings"])


class UpdateProfileRequest(BaseModel):
    user_id: str
    full_name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    theme_preference: Optional[str] = None
    sidebar_mode: Optional[str] = None


class DeleteAllDocumentsRequest(BaseModel):
    user_id: str
    confirmation: str


class DeleteAccountRequest(BaseModel):
    user_id: str
    confirmation: str


def _resolve_authenticated_user_id(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization token")
    try:
        user_resp = supabase.auth.get_user(token)
        auth_user = user_resp.user if user_resp else None
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Failed to validate session: {exc}") from exc
    if not auth_user or not getattr(auth_user, "id", None):
        raise HTTPException(status_code=401, detail="Invalid session")
    return str(auth_user.id)


@router.get("/settings/profile")
def get_settings_profile(user_id: str, authorization: str | None = Header(default=None)):
    auth_user_id = _resolve_authenticated_user_id(authorization)
    if auth_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = []
    for cols in (
        "id, email, name, role, theme_preference, sidebar_mode",
        "id, email, name, role, theme, sidebar_mode",
        "id, email, name, role",
        "id, email, name",
    ):
        try:
            rows = (
                supabase_execute(
                    supabase.table("users")
                    .select(cols)
                    .eq("id", user_id)
                    .limit(1)
                ).data
                or []
            )
            break
        except Exception:
            continue
    if not rows:
        return {"id": user_id, "email": None, "name": "", "role": "Legal Analyst", "theme_preference": "system", "sidebar_mode": "expanded"}
    row = rows[0]
    return {
        "id": row.get("id"),
        "email": row.get("email"),
        "name": row.get("name") or "",
        "role": row.get("role") or "Legal Analyst",
        "theme_preference": row.get("theme_preference") or row.get("theme") or "system",
        "sidebar_mode": row.get("sidebar_mode") or "expanded",
    }


@router.put("/settings/profile")
def update_settings_profile(payload: UpdateProfileRequest, authorization: str | None = Header(default=None)):
    auth_user_id = _resolve_authenticated_user_id(authorization)
    if auth_user_id != payload.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    update_payload = {
        "id": payload.user_id,
        "name": payload.full_name.strip(),
        "role": payload.role.strip(),
        "theme_preference": payload.theme_preference or "system",
        "sidebar_mode": payload.sidebar_mode or "expanded",
    }
    try:
        supabase_execute(supabase.table("users").upsert(update_payload, on_conflict="id"))
    except Exception:
        # Fallback for schemas that use `theme` instead of `theme_preference`.
        fallback_payload = {
            "id": payload.user_id,
            "name": payload.full_name.strip(),
            "role": payload.role.strip(),
            "theme": payload.theme_preference or "system",
            "sidebar_mode": payload.sidebar_mode or "expanded",
        }
        try:
            supabase_execute(supabase.table("users").upsert(fallback_payload, on_conflict="id"))
        except Exception:
            fallback_payload = {
                "id": payload.user_id,
                "name": payload.full_name.strip(),
            }
            supabase_execute(supabase.table("users").upsert(fallback_payload, on_conflict="id"))
    return {"ok": True}


@router.post("/settings/delete-all-documents")
def delete_all_documents(payload: DeleteAllDocumentsRequest, authorization: str | None = Header(default=None)):
    auth_user_id = _resolve_authenticated_user_id(authorization)
    if auth_user_id != payload.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if payload.confirmation.strip().upper() != "DELETE":
        raise HTTPException(status_code=400, detail="Confirmation must be DELETE")

    docs = document_service.list_documents(user_id=payload.user_id, limit=2000)
    deleted_count = 0
    for doc in docs:
        doc_id = doc.get("id") or doc.get("document_id")
        if not doc_id:
            continue
        if document_service.delete_document_cascade(document_id=doc_id):
            deleted_count += 1

    return {"ok": True, "deleted_documents": deleted_count}


@router.post("/settings/delete-account")
def delete_account(payload: DeleteAccountRequest, authorization: str | None = Header(default=None)):
    auth_user_id = _resolve_authenticated_user_id(authorization)
    if auth_user_id != payload.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if payload.confirmation.strip().upper() != "DELETE":
        raise HTTPException(status_code=400, detail="Confirmation must be DELETE")

    # First delete all user documents and related analysis artifacts.
    docs = document_service.list_documents(user_id=payload.user_id, limit=2000)
    for doc in docs:
        doc_id = doc.get("id") or doc.get("document_id")
        if doc_id:
            document_service.delete_document_cascade(document_id=doc_id)

    # Remove profile row (best-effort).
    try:
        supabase_execute(supabase.table("users").delete().eq("id", payload.user_id))
    except Exception:
        pass

    # Remove auth account through admin API (requires service role).
    try:
        supabase.auth.admin.delete_user(payload.user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete auth account: {exc}") from exc

    return {"ok": True}

