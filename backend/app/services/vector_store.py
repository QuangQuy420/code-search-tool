"""Pinecone vector database integration for code search.

Provides functions to upsert, search, and delete code chunk vectors
in a Pinecone index, using namespace-per-repo isolation.

Configuration:
    PINECONE_API_KEY: API key for Pinecone authentication (env var)
    PINECONE_INDEX_NAME: Name of the Pinecone index (env var)

Index configuration: 384 dimensions, cosine similarity.
"""

from __future__ import annotations

from typing import Any

from pinecone import Pinecone, ServerlessSpec

from app.config import settings

VECTOR_DIMENSION = 384
SIMILARITY_METRIC = "cosine"

REQUIRED_METADATA_FIELDS = {
    "file_path",
    "function_name",
    "start_line",
    "end_line",
    "code",
    "language",
    "repo_name",
    "chunk_type",
}


def _get_client() -> Pinecone:
    """Create and return a Pinecone client."""
    if not settings.PINECONE_API_KEY:
        raise ValueError(
            "PINECONE_API_KEY environment variable is not set. "
            "Please set it before using the vector store."
        )
    return Pinecone(api_key=settings.PINECONE_API_KEY)


def _get_or_create_index(client: Pinecone) -> Any:
    """Get existing index or create one with the configured settings."""
    existing_indexes = [idx.name for idx in client.list_indexes()]

    if settings.PINECONE_INDEX_NAME not in existing_indexes:
        client.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=VECTOR_DIMENSION,
            metric=SIMILARITY_METRIC,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    return client.Index(settings.PINECONE_INDEX_NAME)


def _validate_vector(vector: dict) -> None:
    """Validate that a vector dict has all required fields."""
    if "id" not in vector:
        raise ValueError("Vector must have an 'id' field.")
    if "values" not in vector:
        raise ValueError("Vector must have a 'values' field.")
    if len(vector["values"]) != VECTOR_DIMENSION:
        raise ValueError(
            f"Vector dimension mismatch: expected {VECTOR_DIMENSION}, "
            f"got {len(vector['values'])}."
        )

    metadata = vector.get("metadata", {})
    missing = REQUIRED_METADATA_FIELDS - set(metadata.keys())
    if missing:
        raise ValueError(f"Vector metadata is missing required fields: {missing}")


def upsert_vectors(vectors: list[dict]) -> dict:
    """Store vectors with metadata in Pinecone.

    Vectors are grouped by repo_name and upserted into
    the corresponding namespace for isolation.
    """
    for v in vectors:
        _validate_vector(v)

    by_namespace: dict[str, list[dict]] = {}
    for v in vectors:
        repo = v["metadata"]["repo_name"]
        by_namespace.setdefault(repo, []).append(v)

    client = _get_client()
    index = _get_or_create_index(client)

    results: dict[str, Any] = {}
    batch_size = 100

    for namespace, ns_vectors in by_namespace.items():
        for i in range(0, len(ns_vectors), batch_size):
            batch = ns_vectors[i : i + batch_size]
            upsert_data = [
                (v["id"], v["values"], v["metadata"]) for v in batch
            ]
            response = index.upsert(vectors=upsert_data, namespace=namespace)
            if namespace not in results:
                results[namespace] = {"upserted_count": 0}
            results[namespace]["upserted_count"] += response.get(
                "upserted_count", len(batch)
            )

    return results


def search(
    query_vector: list[float],
    top_k: int = 5,
    repo_name: str | None = None,
    filter_metadata: dict | None = None,
) -> list[dict]:
    """Find nearest neighbors for a query vector."""
    if len(query_vector) != VECTOR_DIMENSION:
        raise ValueError(
            f"Query vector dimension mismatch: expected {VECTOR_DIMENSION}, "
            f"got {len(query_vector)}."
        )

    client = _get_client()
    index = _get_or_create_index(client)

    query_kwargs: dict[str, Any] = {
        "vector": query_vector,
        "top_k": top_k,
        "include_metadata": True,
    }
    if repo_name:
        query_kwargs["namespace"] = repo_name
    if filter_metadata:
        query_kwargs["filter"] = filter_metadata

    response = index.query(**query_kwargs)

    return [
        {
            "id": match["id"],
            "score": match["score"],
            "metadata": match.get("metadata", {}),
        }
        for match in response.get("matches", [])
    ]


def delete_by_repo(repo_name: str) -> None:
    """Delete all vectors for a given repo (for re-indexing)."""
    if not repo_name:
        raise ValueError("repo_name must not be empty.")

    client = _get_client()
    index = _get_or_create_index(client)

    index.delete(delete_all=True, namespace=repo_name)
