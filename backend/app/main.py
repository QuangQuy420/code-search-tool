import logging
import time
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.services.embedder import embed_text
from app.services.explainer import explain_code
from app.services.indexer import index_repo, list_indexed_repos, validate_repo_url
from app.services.vector_store import search as vector_search

logger = logging.getLogger("code_search_tool")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Code Search Tool", version="0.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        errors.append({"field": field, "message": error.get("msg", "")})
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Handle Pinecone errors
    try:
        from pinecone.exceptions import PineconeException

        if isinstance(exc, PineconeException):
            logger.error("Pinecone error: %s", exc)
            return JSONResponse(
                status_code=503,
                content={"detail": "Vector database service is temporarily unavailable"},
            )
    except ImportError:
        pass

    # Handle Groq API errors
    try:
        from groq import APIError as GroqAPIError
        from groq import RateLimitError as GroqRateLimitError

        if isinstance(exc, GroqRateLimitError):
            logger.warning("Groq rate limit hit: %s", exc)
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "LLM service rate limit exceeded. Please try again later.",
                },
            )
        if isinstance(exc, GroqAPIError):
            logger.error("Groq API error: %s", exc)
            return JSONResponse(
                status_code=503,
                content={"detail": "LLM service is temporarily unavailable"},
            )
    except ImportError:
        pass

    # Fallback: generic 500
    logger.error(
        "Unhandled exception on %s %s:\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


class IndexRequest(BaseModel):
    repo_url: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    repo_name: str | None = None


class ExplainRequest(BaseModel):
    code: str
    language: str
    function_name: str


@app.post("/api/index")
async def index_repository(request: IndexRequest):
    """Clone a GitHub repo, parse, embed, and store in Pinecone."""
    if not validate_repo_url(request.repo_url):
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid GitHub repo URL. Expected: https://github.com/owner/repo"},
        )
    try:
        result = index_repo(request.repo_url)
        return result
    except RuntimeError as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/api/repos")
async def get_repos():
    """List all indexed repositories."""
    repos = list_indexed_repos()
    return {"repos": repos}


@app.post("/api/search")
async def search_code(request: SearchRequest):
    """Search indexed code with a natural language query."""
    if not request.query.strip():
        return JSONResponse(
            status_code=422,
            content={"detail": "Query must not be empty."},
        )
    if not 1 <= request.top_k <= 20:
        return JSONResponse(
            status_code=422,
            content={"detail": "top_k must be between 1 and 20."},
        )

    query_vector = embed_text(request.query)
    matches = vector_search(
        query_vector=query_vector,
        top_k=request.top_k,
        repo_name=request.repo_name,
    )

    results = []
    for match in matches:
        meta = match.get("metadata", {})
        results.append({
            "score": match.get("score", 0),
            "file_path": meta.get("file_path", ""),
            "function_name": meta.get("function_name", ""),
            "start_line": meta.get("start_line", 0),
            "end_line": meta.get("end_line", 0),
            "code": meta.get("code", ""),
            "language": meta.get("language", ""),
            "chunk_type": meta.get("chunk_type", ""),
            "repo_name": meta.get("repo_name", ""),
        })

    return {"results": results}


@app.post("/api/explain")
async def explain(request: ExplainRequest):
    """Stream an LLM-powered code explanation via Server-Sent Events."""

    async def _event_generator():
        try:
            async for token in explain_code(
                code=request.code,
                language=request.language,
                function_name=request.function_name,
            ):
                yield {"data": token}
        except ValueError as exc:
            yield {"event": "error", "data": str(exc)}
        except Exception as exc:
            error_msg = str(exc)
            if "rate limit" in error_msg.lower():
                yield {
                    "event": "error",
                    "data": "Groq rate limit exceeded. Please try again later.",
                }
            else:
                yield {"event": "error", "data": f"An error occurred: {error_msg}"}

    return EventSourceResponse(_event_generator())


@app.get("/health")
async def health_check():
    return {"status": "ok"}
