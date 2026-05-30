from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4


ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def sanitize_filename(name: str) -> str:
    # Keep it simple and storage-safe.
    name = name.strip().replace("\\", "_").replace("/", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name[:180] if len(name) > 180 else name


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def ensure_allowed_file(filename: str) -> None:
    ext = get_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")


def build_storage_path(user_id: str | None, original_filename: str) -> tuple[str, str]:
    """
    Returns (object_path, document_id).
    Object path format: {user_or_public}/{document_id}/{filename}
    """
    document_id = str(uuid4())
    safe_name = sanitize_filename(original_filename) or f"document{get_extension(original_filename)}"
    base = user_id or "public"
    object_path = f"{base}/{document_id}/{safe_name}"
    return object_path, document_id

