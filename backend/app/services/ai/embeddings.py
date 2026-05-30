from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


def embedding_dimension() -> int:
    m = _model()
    return int(m.get_sentence_embedding_dimension())


def encode_texts(texts: list[str], *, batch_size: int = 32) -> np.ndarray:
    if not texts:
        return np.array([])
    m = _model()
    emb = m.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(emb, dtype=np.float32)
