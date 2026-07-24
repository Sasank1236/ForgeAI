# ForgeAI

> **Repository-Aware AI Coding Assistant** — Version 1.0 MVP

ForgeAI helps developers understand unfamiliar repositories, search code intelligently, plan implementation tasks, and get AI-powered code suggestions — all grounded in a deep understanding of the actual repository structure.

---

## Features (v1.0)

| Feature | Description |
|---|---|
| Repository Import | Scan and index local repositories |
| Repository Parser | Extract functions, classes, methods, imports via Tree-sitter |
| Knowledge Base | Build vector embeddings for semantic understanding |
| Repository Search | Semantic + keyword + symbol + file search |
| Repository Chat | Ask questions, get context-grounded answers |
| Task Planner | Generate structured implementation plans |
| Code Suggestions | AI-generated code hints (no auto-modification) |
| Documentation | Auto-generated architecture and file summaries |
| Dashboard | Repository overview, language stats, dependency graph |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 async |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Parser | Tree-sitter |
| LLM | OpenAI GPT-4o via LiteLLM |
| Embeddings | OpenAI text-embedding-3-small |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Dev Infra | Docker Compose |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- uv (`pip install uv`)

### 1. Clone and configure

```bash
git clone <repo-url>
cd forgeai
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 2. Start dev infrastructure

```bash
docker compose up -d
```

This starts:
- PostgreSQL 16 + pgvector on `localhost:5432`
- Redis 7 on `localhost:6379`

### 3. Start the backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn src.forgeai.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

App available at: http://localhost:3000

---

## Project Structure

```
forgeai/
├── backend/          # FastAPI Python backend
├── frontend/         # Next.js TypeScript frontend
├── docker/           # Additional Docker configs
├── docs/             # Architecture documentation
└── docker-compose.yml
```

---

## Architecture

Clean architecture layers:
```
Router → Service → Repository Layer → Database
           ↕
        Schema (Pydantic DTOs)
```

---

## Development

### Running tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm test
```

### Linting

```bash
cd backend && uv run ruff check .
cd frontend && npm run lint
```

---

## License

MIT
