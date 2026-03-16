"""GitHub repo cloning and indexing pipeline.

Orchestrates: clone repo → parse with tree-sitter → embed chunks → store in Pinecone.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path

from app.services.embedder import embed_batch, format_chunk_text
from app.services.parser import (
    EXTENSION_TO_LANGUAGE,
    CodeChunk,
    parse_file,
    should_skip_file,
)
from app.services.vector_store import (
    delete_by_repo,
    upsert_vectors,
    _get_client,
    _get_or_create_index,
)

logger = logging.getLogger("code_search_tool.indexer")

GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[\w.\-]+/[\w.\-]+/?$"
)


def validate_repo_url(repo_url: str) -> bool:
    """Check that repo_url is a valid GitHub HTTPS URL."""
    return bool(GITHUB_URL_PATTERN.match(repo_url.rstrip("/")))


def extract_repo_name(repo_url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    url = repo_url.rstrip("/")
    parts = url.split("/")
    return f"{parts[-2]}/{parts[-1]}"


def _clone_repo(repo_url: str, dest: str) -> None:
    """Shallow-clone a public GitHub repo."""
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--", repo_url, dest],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
    except subprocess.TimeoutExpired as exc:
        logger.error(
            "Git clone timeout",
            extra={"repo_url": repo_url, "timeout_seconds": 120}
        )
        raise RuntimeError(f"git clone timeout after 120 seconds: {repo_url}") from exc


def _find_source_files(root: str) -> list[str]:
    """Recursively find all supported source files."""
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skip dirs in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in {
                "node_modules", ".git", ".venv", "__pycache__", ".next",
                "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
                "vendor", "target",
            }
        ]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            ext = Path(fname).suffix.lower()
            if ext in EXTENSION_TO_LANGUAGE and not should_skip_file(fpath):
                files.append(fpath)
    return files


def _make_vector_id(repo_name: str, file_path: str, function_name: str, start_line: int) -> str:
    """Create a deterministic vector ID."""
    raw = f"{repo_name}:{file_path}:{function_name}:{start_line}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def index_repo(repo_url: str) -> dict:
    """Run the full indexing pipeline for a GitHub repo.

    Returns a summary dict with chunk and vector counts.
    """
    if not validate_repo_url(repo_url):
        raise ValueError(f"Invalid GitHub repo URL: {repo_url}")

    repo_name = extract_repo_name(repo_url)
    logger.info(
        "Starting repo indexing",
        extra={"repo_url": repo_url, "repo_name": repo_name}
    )

    # Delete existing vectors for re-indexing
    try:
        delete_by_repo(repo_name)
        logger.info(
            "Cleared existing vectors",
            extra={"repo_name": repo_name}
        )
    except Exception as exc:
        logger.debug(
            "No existing vectors to clear",
            extra={"repo_name": repo_name, "error": str(exc)}
        )

    tmp_dir = tempfile.mkdtemp(prefix="code_search_")
    try:
        # Clone
        logger.info(
            "Starting git clone",
            extra={"repo_url": repo_url, "repo_name": repo_name}
        )
        _clone_repo(repo_url, tmp_dir)
        logger.info(
            "Repo cloned successfully",
            extra={"repo_name": repo_name}
        )

        # Find source files
        source_files = _find_source_files(tmp_dir)
        logger.info(
            "Source files discovered",
            extra={"repo_name": repo_name, "file_count": len(source_files)}
        )

        if not source_files:
            logger.warning(
                "No source files found",
                extra={"repo_name": repo_name}
            )
            return {
                "repo_name": repo_name,
                "files_found": 0,
                "chunks_parsed": 0,
                "vectors_stored": 0,
            }

        # Parse all files
        logger.info(
            "Parsing source files",
            extra={"repo_name": repo_name, "file_count": len(source_files)}
        )
        all_chunks: list[CodeChunk] = []
        for fpath in source_files:
            # Use relative path for storage
            rel_path = os.path.relpath(fpath, tmp_dir)
            chunks = parse_file(fpath)
            for chunk in chunks:
                # Replace absolute path with relative
                all_chunks.append(CodeChunk(
                    code=chunk.code,
                    file_path=rel_path,
                    function_name=chunk.function_name,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    language=chunk.language,
                    chunk_type=chunk.chunk_type,
                ))
        logger.info(
            "Parsing complete",
            extra={"repo_name": repo_name, "chunk_count": len(all_chunks)}
        )

        if not all_chunks:
            logger.warning(
                "No code chunks parsed",
                extra={"repo_name": repo_name, "file_count": len(source_files)}
            )
            return {
                "repo_name": repo_name,
                "files_found": len(source_files),
                "chunks_parsed": 0,
                "vectors_stored": 0,
            }

        # Embed
        logger.info(
            "Embedding chunks",
            extra={"repo_name": repo_name, "chunk_count": len(all_chunks)}
        )
        texts = [
            format_chunk_text(c.chunk_type, c.function_name, c.code)
            for c in all_chunks
        ]
        embeddings = embed_batch(texts)
        logger.info(
            "Embedding complete",
            extra={"repo_name": repo_name, "embedding_count": len(embeddings)}
        )

        # Build vectors for Pinecone
        vectors = []
        for chunk, embedding in zip(all_chunks, embeddings):
            vectors.append({
                "id": _make_vector_id(repo_name, chunk.file_path, chunk.function_name, chunk.start_line),
                "values": embedding,
                "metadata": {
                    "file_path": chunk.file_path,
                    "function_name": chunk.function_name,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "code": chunk.code[:1000],  # Truncate long code for metadata limits
                    "language": chunk.language,
                    "repo_name": repo_name,
                    "chunk_type": chunk.chunk_type,
                },
            })

        # Upsert to Pinecone
        logger.info(
            "Upserting vectors",
            extra={"repo_name": repo_name, "vector_count": len(vectors)}
        )
        result = upsert_vectors(vectors)
        total_upserted = sum(ns.get("upserted_count", 0) for ns in result.values())
        logger.info(
            "Indexing complete",
            extra={
                "repo_name": repo_name,
                "files_found": len(source_files),
                "chunks_parsed": len(all_chunks),
                "vectors_stored": total_upserted,
            }
        )

        return {
            "repo_name": repo_name,
            "files_found": len(source_files),
            "chunks_parsed": len(all_chunks),
            "vectors_stored": total_upserted,
        }
    except Exception as exc:
        logger.error(
            "Indexing failed",
            extra={
                "repo_name": repo_name,
                "repo_url": repo_url,
                "exception": traceback.format_exc(),
            }
        )
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def list_indexed_repos() -> list[dict]:
    """List all indexed repos by querying Pinecone namespace stats."""
    try:
        client = _get_client()
        index = _get_or_create_index(client)
        stats = index.describe_index_stats()
        repos = []
        for namespace, ns_stats in (stats.get("namespaces", {}) or {}).items():
            if namespace:  # skip default empty namespace
                repos.append({
                    "repo_name": namespace,
                    "vector_count": ns_stats.get("vector_count", 0),
                })
        return repos
    except Exception as exc:
        logger.error("Failed to list repos: %s", exc)
        return []
