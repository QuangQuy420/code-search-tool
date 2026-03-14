FROM python:3.11-slim AS builder

# Install system dependencies for tree-sitter and git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc g++ make \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install Python dependencies (use system Python, not uv-managed)
RUN uv sync --frozen --no-dev --python-preference=only-system

# Pre-cache the sentence-transformers model at build time
RUN uv run --python-preference=only-system python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uv", "run", "--python-preference=only-system", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
