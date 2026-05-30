from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    if not settings.pinecone_api_key:
        return None
    try:
        from pinecone import Pinecone

        return Pinecone(api_key=settings.pinecone_api_key)
    except Exception as e:
        logger.warning("Pinecone client init failed: %s", e)
        return None


def get_index():
    pc = _client()
    if not pc:
        return None
    name = settings.pinecone_index_name
    try:
        if settings.pinecone_host:
            return pc.Index(name, host=settings.pinecone_host)
        return pc.Index(name)
    except Exception as e:
        logger.warning("Pinecone Index(%s) failed: %s", name, e)
        return None


def upsert_vectors(
    vectors: list[tuple[str, list[float], dict[str, Any]]],
    *,
    batch_size: int = 100,
) -> None:
    """
    vectors: list of (vector_id, values, metadata)
    """
    index = get_index()
    if not index or not vectors:
        if not settings.pinecone_api_key:
            logger.info("PINECONE_API_KEY not set; skipping vector upsert")
        return
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        payload = [
            {"id": vid, "values": vals, "metadata": meta}
            for vid, vals, meta in batch
        ]
        try:
            index.upsert(vectors=payload)
        except Exception as e:
            logger.error("Pinecone upsert failed: %s", e)


def delete_vector_ids(vector_ids: list[str], *, batch_size: int = 100) -> None:
    """Remove vectors by id (e.g. document_chunks.pinecone_vector_id)."""
    index = get_index()
    if not index or not vector_ids:
        if not settings.pinecone_api_key:
            logger.debug("PINECONE_API_KEY not set; skipping vector delete")
        return
    for i in range(0, len(vector_ids), batch_size):
        batch = vector_ids[i : i + batch_size]
        try:
            index.delete(ids=batch)
        except Exception as e:
            logger.warning("Pinecone delete batch failed: %s", e)
