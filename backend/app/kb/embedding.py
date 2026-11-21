"""Local embedding model.

Runs on CPU through fastembed and needs no API key. The model is downloaded
once (at image build time, see Dockerfile) and cached in the image, so the
demo machine does not need internet at run time.

The knowledge base ships with embeddings already computed in
``data/kb/*.jsonl``; this module is used when ingesting new content and for
embedding the query at search time.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

# Multilingual (Turkish included), small, CPU-friendly, 384 dimensions -
# matches kb_chunk.embedding. Chosen from fastembed's supported list so the
# model can be baked into the image.
MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
EMBEDDING_DIM = 384


class EmbeddingUnavailable(RuntimeError):
    """Raised with a Turkish message when the model cannot be loaded."""


@lru_cache(maxsize=1)
def _model():
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise EmbeddingUnavailable(
            "fastembed kurulu değil; vektör araması kullanılamıyor."
        ) from exc
    try:
        return TextEmbedding(model_name=MODEL_NAME)
    except Exception as exc:  # noqa: BLE001
        raise EmbeddingUnavailable(
            "Yerel embedding modeli yüklenemedi. İlk çalıştırmada model "
            "indirilemediyse internet bağlantısını kontrol edip imajı yeniden "
            "oluşturun. Arama bu sırada yalnızca anahtar kelimeyle çalışır.",
        ) from exc


def is_available() -> bool:
    try:
        _model()
        return True
    except EmbeddingUnavailable:
        return False


def embed_documents(texts: list[str]) -> list[list[float]]:
    model = _model()
    return [[float(value) for value in vector] for vector in model.embed(texts)]


def embed_query(text: str) -> list[float]:
    model = _model()
    vector = next(iter(model.embed([text])))
    return [float(value) for value in vector]
