from collections.abc import AsyncGenerator
import logging

from groq import AsyncGroq, RateLimitError

from app.config import settings

logger = logging.getLogger("code_search_tool.explainer")

PROMPT_TEMPLATE = """\
You are an expert software engineer. A user has asked you to explain the following \
{language} function named `{function_name}`.

```{language}
{code}
```

Please provide a clear explanation that covers:
1. **What the code does** — explain the overall purpose in plain English.
2. **Key logic and patterns** — walk through the important steps, data structures, \
algorithms, or design patterns used.
3. **Potential edge cases** — mention any edge cases, failure modes, or unexpected \
inputs that could affect behaviour.

Be concise but thorough.\
"""


async def explain_code(
    code: str,
    language: str,
    function_name: str,
) -> AsyncGenerator[str, None]:
    """Stream an LLM-generated explanation of the given code snippet.

    Yields text chunks as they arrive from the Groq API.
    """
    api_key = settings.GROQ_API_KEY
    if not api_key:
        logger.error("GROQ_API_KEY is not set")
        raise ValueError("GROQ_API_KEY environment variable is not set")

    logger.info(
        "Starting code explanation",
        extra={
            "language": language,
            "function_name": function_name,
            "code_length": len(code),
        }
    )

    client = AsyncGroq(api_key=api_key)

    prompt = PROMPT_TEMPLATE.format(
        language=language,
        function_name=function_name,
        code=code,
    )

    token_count = 0
    try:
        logger.debug(
            "Requesting streaming explanation from Groq",
            extra={
                "language": language,
                "function_name": function_name,
                "model": "llama-3.1-8b-instant",
            }
        )

        stream = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        logger.debug(
            "Streaming explanation started",
            extra={
                "language": language,
                "function_name": function_name,
            }
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                token_count += len(delta.content.split())
                yield delta.content

        logger.info(
            "Code explanation completed",
            extra={
                "language": language,
                "function_name": function_name,
                "estimated_token_count": token_count,
            }
        )

    except RateLimitError as exc:
        logger.warning(
            "Groq rate limit exceeded",
            extra={
                "language": language,
                "function_name": function_name,
            }
        )
        raise RateLimitError(
            message=f"Groq rate limit exceeded. Please try again later. Details: {exc.message}",
            response=exc.response,
            body=exc.body,
        )
    except Exception as exc:
        logger.error(
            "Code explanation failed",
            extra={
                "language": language,
                "function_name": function_name,
                "error": str(exc),
            }
        )
        raise
