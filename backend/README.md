# Code Search Tool — Backend

FastAPI backend for semantic code search. Index GitHub repositories, search code with natural language queries, and get AI-powered explanations.

## Tech Stack

- **Python** >=3.13 with **FastAPI**
- **uv** — package manager
- **Pinecone** — vector database (cosine similarity)
- **Sentence Transformers** — embeddings (all-MiniLM-L6-v2, 384-dim)
- **Tree-sitter** — code parsing (Python, JS, TS, Java, Go, Rust)
- **Groq** — LLM code explanations (llama-3.1-8b, SSE streaming)

## Project Structure

```
backend/
├── app/
│   ├── config.py              # Pydantic settings (env vars)
│   ├── main.py                # FastAPI app, routes, middleware
│   └── services/
│       ├── parser.py          # Tree-sitter code parser
│       ├── embedder.py        # Sentence-transformers embeddings
│       ├── indexer.py         # GitHub repo clone + indexing pipeline
│       ├── explainer.py       # Groq LLM explanation (SSE streaming)
│       └── vector_store.py    # Pinecone vector DB operations
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── .env.example
```

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Pinecone account and API key
- Groq account and API key

## Getting Started

```bash
cd backend

# 1. Configure environment
cp .env.example .env
# Edit .env and fill in your API keys

# 2. Install dependencies
uv sync

# 3. Start development server
uv run uvicorn app.main:app --reload
```

The server runs at **http://localhost:8000**.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PINECONE_API_KEY` | Pinecone API key | — |
| `PINECONE_INDEX_NAME` | Pinecone index name | `code-search-tool` |
| `GROQ_API_KEY` | Groq API key for LLM explanations | — |
| `ALLOWED_ORIGINS` | CORS allowed origins | `["http://localhost:3000"]` |

## API Endpoints

### `POST /api/index`
Clone a GitHub repo, parse code, generate embeddings, and store in Pinecone.
```json
{ "repo_url": "https://github.com/owner/repo" }
```

### `GET /api/repos`
List all indexed repositories.

### `POST /api/search`
Search indexed code with a natural language query.
```json
{ "query": "function that handles authentication", "top_k": 5, "repo_name": "owner/repo" }
```

### `POST /api/explain`
Stream an AI-powered code explanation via Server-Sent Events.
```json
{ "code": "def foo(): ...", "language": "python", "function_name": "foo" }
```

### `GET /health`
Health check endpoint. Returns `{"status": "ok"}`.

## Docker

```bash
# Build
docker build -t code-search-backend .

# Run
docker run -p 8000:8000 --env-file .env code-search-backend
```
