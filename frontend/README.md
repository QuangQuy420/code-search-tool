# Code Search Tool — Frontend

Next.js frontend for semantic code search. Search indexed repositories with natural language and get AI-powered code explanations.

## Tech Stack

- **Next.js** 16 with App Router
- **React** 19
- **TypeScript** 5
- **Tailwind CSS** 4
- **react-syntax-highlighter** — code display

## Features

- Natural language code search across indexed repos
- Repository selector to filter search results
- Syntax-highlighted code in search results
- AI-powered code explanations via SSE streaming
- Repo indexing page to add new GitHub repositories

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Home / search page
│   │   └── repos/
│   │       └── page.tsx         # Repo indexing page
│   ├── components/
│   │   ├── SearchBar.tsx        # Search input
│   │   ├── RepoSelector.tsx     # Repository selector dropdown
│   │   ├── ResultsList.tsx      # Search results list
│   │   └── ResultCard.tsx       # Result card with code display
│   ├── lib/
│   │   └── api.ts               # API client (backend fetch calls)
│   └── types/
│       └── search.ts            # TypeScript type definitions
├── public/
├── package.json
├── next.config.ts
├── tsconfig.json
├── postcss.config.mjs
├── vercel.json
└── .env.example
```

## Prerequisites

- Node.js 18+
- npm
- Backend server running (see `../backend/README.md`)

## Getting Started

```bash
cd frontend

# 1. Configure environment
cp .env.example .env.local
# Edit .env.local if your backend runs on a different URL

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

The app runs at **http://localhost:3000**.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm start` | Start production server |
| `npm run lint` | Run ESLint |

## Deployment

The project is configured for **Vercel** deployment (`vercel.json` included). Connect your GitHub repo to Vercel and set `NEXT_PUBLIC_API_URL` in the Vercel environment variables.
