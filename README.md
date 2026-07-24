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
│   ├── src/forgeai/
│   │   ├── api/v1/   # REST routers (health, repositories)
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic DTOs
│   │   ├── services/ # Business logic (scanner, repository_service)
│   │   └── repositories/ # Data access layer
│   └── alembic/      # Database migrations
├── frontend/         # Next.js TypeScript frontend
│   └── src/app/
│       ├── page.tsx       # Landing page
│       └── dashboard/     # Repository dashboard (Phase 2)
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

## Phase 2 — Repository Import & File Scanner

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/repositories/import` | Import & scan a local path |
| `GET` | `/api/v1/repositories` | List all repositories with stats |
| `GET` | `/api/v1/repositories/{id}` | Single repository detail |
| `GET` | `/api/v1/repositories/{id}/files` | Paginated file list |
| `DELETE` | `/api/v1/repositories/{id}` | Delete repository and files |

### Import a repository

```bash
curl -X POST http://localhost:8000/api/v1/repositories/import \
  -H 'Content-Type: application/json' \
  -d '{"path": "/absolute/path/to/repo"}'
```

Response:
```json
{
  "repository_id": "uuid",
  "status": "ready",
  "files_scanned": 428,
  "languages": { "Python": 92, "TypeScript": 61, "Markdown": 18 },
  "scan_time_ms": 1432
}
```

### Scanner configuration

The scanner ignores these directories by default:
`node_modules`, `.git`, `__pycache__`, `.next`, `dist`, `build`, `.venv`, `venv`

Language detection is driven by a `LANGUAGE_MAP` in `services/scanner.py`.
Adding new extensions requires no code changes outside that file.

### Repository Dashboard

Open http://localhost:3000/dashboard to:
- Import a repository by local path
- View scan status, file count, language distribution
- Inspect per-language file counts with a visual bar
- Delete a repository

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
