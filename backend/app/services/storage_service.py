from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from app.config import settings
from app.services.supabase_service import supabase

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredFile:
    bucket: str
    object_path: str
    public_url: str


class StorageService:
    def __init__(self, bucket: str | None = None):
        self.bucket = bucket or settings.supabase_storage_bucket

    def upload_bytes(self, object_path: str, content: bytes, content_type: str | None = None) -> StoredFile:
        file_options = {}
        if content_type:
            file_options["content-type"] = content_type

        supabase.storage.from_(self.bucket).upload(
            path=object_path,
            file=content,
            file_options=file_options or None,
        )

        public_url = supabase.storage.from_(self.bucket).get_public_url(object_path)
        return StoredFile(bucket=self.bucket, object_path=object_path, public_url=public_url)

    def download_bytes(self, object_path: str) -> bytes:
        return supabase.storage.from_(self.bucket).download(object_path)

    def object_path_from_public_url(self, public_url: str) -> str | None:
        """Resolve storage object path from a Supabase public object URL."""
        if not public_url or not public_url.strip():
            return None
        path = urlparse(public_url.strip()).path
        needle = f"/object/public/{self.bucket}/"
        if needle not in path:
            return None
        idx = path.index(needle) + len(needle)
        decoded = unquote(path[idx:]).strip("/")
        return decoded or None

    def delete_file_by_public_url(self, public_url: str) -> None:
        object_path = self.object_path_from_public_url(public_url)
        if not object_path:
            logger.warning("Could not parse storage path from URL; skipping storage delete")
            return
        try:
            supabase.storage.from_(self.bucket).remove([object_path])
        except Exception as e:
            logger.warning("Storage remove failed for %s: %s", object_path, e)


storage_service = StorageService()

