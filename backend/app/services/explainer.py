import os
from collections.abc import AsyncGenerator

from groq import AsyncGroq, RateLimitError


GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

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
    api_key = GROQ_API_KEY
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")

    client = AsyncGroq(api_key=api_key)

    prompt = PROMPT_TEMPLATE.format(
        language=language,
        function_name=function_name,
        code=code,
    )

    try:
        stream = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except RateLimitError as exc:
        raise RateLimitError(
            message=f"Groq rate limit exceeded. Please try again later. Details: {exc.message}",
            response=exc.response,
            body=exc.body,
        )
