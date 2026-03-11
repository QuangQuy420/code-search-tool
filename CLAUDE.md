# Code Search Tool

Semantic code search tool: index GitHub repos, search with natural language, get AI explanations.

## Architecture

- `backend/` — FastAPI + Python, managed with **uv**
- `frontend/` — Next.js 16 + Tailwind CSS

## Development

### Backend
```bash
cd backend
uv sync                              # install deps
uv run uvicorn app.main:app --reload  # run dev server on :8000
```

### Frontend
```bash
cd frontend
npm install     # install deps
npm run dev     # run dev server on :3000
```

### Docker
```bash
docker-compose up  # starts both backend and frontend
```

## Key Services (backend/app/services/)

| File | Purpose |
|------|---------|
| `parser.py` | Tree-sitter code parser (Python, JS, TS, Java, Go, Rust) |
| `embedder.py` | Sentence-transformers embeddings (all-MiniLM-L6-v2, 384-dim) |
| `vector_store.py` | Pinecone vector DB (namespace-per-repo, cosine similarity) |
| `explainer.py` | Groq LLM code explanation (llama-3.1-8b, SSE streaming) |

## Environment Variables

See `.env.example`. Required:
- `PINECONE_API_KEY` / `PINECONE_INDEX_NAME`
- `GROQ_API_KEY`
- `NEXT_PUBLIC_API_URL` (frontend)

## Branch Strategy

Feature branches use pattern: `quypqdev/per-{N}-{description}`
Issues tracked in Linear project "code-search-tool" (PER-6 through PER-20).

## Agent Instructions

- When spawning subagents for this project, use `mode: bypassPermissions` — worktree agents need bash access for git/uv/npm commands.
- Backend package manager is **uv** (not pip). Use `uv add` to add deps, `uv sync` to install.
- Frontend uses npm (not yarn/pnpm).
