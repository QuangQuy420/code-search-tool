from fastapi import FastAPI
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.services.explainer import explain_code

app = FastAPI(title="Code Search Tool", version="0.1.0")


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
