"""Embedding service using sentence-transformers.

Provides functions to embed text and code chunks using the
all-MiniLM-L6-v2 model (384-dimensional vectors). The model is loaded
once at startup using a singleton pattern.
"""

from __future__ import annotations

import logging
import time

from sentence_transformers import SentenceTransformer

logger = logging.getLogger("code_search_tool.embedder")

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
BATCH_SIZE = 64

_model: SentenceTransformer | None = None
_model_loaded = False


def _get_model() -> SentenceTransformer:
    """Return the singleton SentenceTransformer model, loading it on first call."""
    global _model, _model_loaded
    if _model is None:
        logger.info(
            "Loading embedding model",
            extra={"model_name": MODEL_NAME}
        )
        start_time = time.time()
        _model = SentenceTransformer(MODEL_NAME)
        load_time_ms = (time.time() - start_time) * 1000
        logger.info(
            "Embedding model loaded",
            extra={
                "model_name": MODEL_NAME,
                "dimension": EMBEDDING_DIM,
                "load_time_ms": round(load_time_ms, 1),
            }
        )
        _model_loaded = True
    return _model


def preload_model() -> None:
    """Eagerly load the embedding model. Call at application startup."""
    _get_model()


def embed_text(text: str) -> list[float]:
    """Embed a single text string and return a list of floats (384-d vector)."""
    model = _get_model()
    start_time = time.time()
    embedding = model.encode(text, show_progress_bar=False)
    duration_ms = (time.time() - start_time) * 1000

    logger.debug(
        "Text embedded",
        extra={
            "input_length": len(text),
            "duration_ms": round(duration_ms, 1),
        }
    )

    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts efficiently.

    For large inputs the texts are processed in chunks of ``BATCH_SIZE``
    (default 64) to keep memory usage reasonable.
    """
    if not texts:
        return []

    model = _get_model()
    start_time = time.time()
    total_input_length = sum(len(t) for t in texts)

    all_embeddings: list[list[float]] = []
    for start_idx in range(0, len(texts), BATCH_SIZE):
        batch = texts[start_idx : start_idx + BATCH_SIZE]
        embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.extend(embeddings.tolist())

    duration_ms = (time.time() - start_time) * 1000

    logger.debug(
        "Batch embedding complete",
        extra={
            "batch_size": len(texts),
            "total_input_length": total_input_length,
            "duration_ms": round(duration_ms, 1),
        }
    )

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
