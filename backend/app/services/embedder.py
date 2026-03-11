"""Embedding service using sentence-transformers.

Provides functions to embed text and code chunks using the
all-MiniLM-L6-v2 model (384-dimensional vectors). The model is loaded
once at startup using a singleton pattern.
"""

from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
BATCH_SIZE = 64

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return the singleton SentenceTransformer model, loading it on first call."""
    global _model
    if _model is None:
        logger.info("Loading embedding model '%s'...", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model loaded (dim=%d).", EMBEDDING_DIM)
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single text string and return a list of floats (384-d vector)."""
    model = _get_model()
    embedding = model.encode(text, show_progress_bar=False)
    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts efficiently.

    For large inputs the texts are processed in chunks of ``BATCH_SIZE``
    (default 64) to keep memory usage reasonable.
    """
    if not texts:
        return []

    model = _get_model()

    all_embeddings: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.extend(embeddings.tolist())

    return all_embeddings


def format_chunk_text(
    chunk_type: str,
    function_name: str,
    code: str,
) -> str:
    """Build the combined string used to embed a code chunk.

    The format is: ``"{chunk_type} {function_name}: {code}"``
    """
    return f"{chunk_type} {function_name}: {code}"
