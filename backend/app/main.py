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
from app.services.explainer import explain_code

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


class ExplainRequest(BaseModel):
    code: str
    language: str
    function_name: str


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
