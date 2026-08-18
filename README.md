# ForgeAI

> **Repository-Aware AI Coding Assistant** — Production Ready v1.0

ForgeAI helps developers understand unfamiliar repositories, search code intelligently, plan implementation tasks, generate code suggestions, auto-synthesize technical documentation, and chat with codebases — all grounded in a deep understanding of actual repository AST structures and vector embeddings.

---

## Features (v1.0)

| Feature | Description |
|---|---|
| **Repository Import & Scanner** | High-speed local directory scanner filtering binary/ignored files with language detection |
| **Tree-sitter AST Parser** | Extracts classes, functions, methods, imports, and signatures across 8+ languages (Python, JS, TS, TSX, Go, Java, C++, Rust) |
| **Vector Knowledge Base** | Sliding-window code chunker and OpenAI text-embedding-3-small vector storage |
| **Multi-Modal Search Engine** | Semantic, BM25 Keyword, AST Symbol, and Reciprocal Rank Fusion (RRF) Hybrid Search |
| **Repository Chat & Grounded QA** | Conversational QA with SSE streaming response, AST symbol grounding, and line-level citations |
| **AI Task Decomposition Planner** | Multi-step task planner and targeted code diff suggestion generator |
| **Auto Documentation Engine** | Synthesizes README.md, Architecture Specs, and API Reference docs with live Markdown editor and `.md` export |
| **Code & Symbol Explorer** | Interactive file explorer and Tree-sitter AST symbol metadata inspector |
| **System Observability Telemetry** | Real-time health probes, database record telemetry, host disk usage, and request tracing (`X-Request-ID`) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python 3.11, FastAPI, Async SQLAlchemy 2.0, Pydantic v2 |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache & In-Memory** | Redis 7 |
| **Code Parser** | Tree-sitter (8 language grammars) |
| **LLM & Embeddings** | OpenAI GPT-4o & `text-embedding-3-small` via LiteLLM |
| **Logging & Tracing** | `structlog` JSON logger & `RequestLoggingMiddleware` |
| **Frontend UI** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide Icons |
| **Dev Infrastructure** | Docker Compose & `uv` Package Manager |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- `uv` Python package manager (`pip install uv`)

### 1. Clone and Configure

```bash
git clone https://github.com/Sasank1236/ForgeAI.git
cd ForgeAI
cp backend/.env.example backend/.env
# Edit backend/.env and set your OPENAI_API_KEY
```

### 2. Start Infrastructure Services

```bash
docker compose up -d
```

This starts:
- PostgreSQL 16 + pgvector on `localhost:5432`
- Redis 7 on `localhost:6379`

### 3. Start Backend API Server

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn src.forgeai.main:app --reload --port 8000
```

- API Interactive Swagger Docs available at: http://localhost:8000/docs
- System Health Telemetry available at: http://localhost:8000/api/v1/health/system

### 4. Start Frontend Web Dashboard

```bash
cd frontend
npm install
npm run dev
```

- Web Dashboard available at: http://localhost:3000

---

## Complete API Reference (v1.0)

### 1. Health & System Telemetry
- `GET /api/v1/health` — Basic liveness probe
- `GET /api/v1/health/system` — Real-time readiness probe, host disk metrics, and database telemetry counts

### 2. Repository Import & File Management
- `POST /api/v1/repositories/import` — Import and scan local directory
- `GET /api/v1/repositories` — List imported repositories with language breakdown
- `GET /api/v1/repositories/{id}` — Get single repository details and stats
- `GET /api/v1/repositories/{id}/files` — Paginated file listing
- `DELETE /api/v1/repositories/{id}` — Delete repository and indexed files

### 3. Tree-sitter AST Code Parsing
- `POST /api/v1/repositories/{id}/parse` — Parse repository files with Tree-sitter
- `GET /api/v1/repositories/{id}/symbols` — List extracted AST code symbols (classes, methods, functions)
- `GET /api/v1/repositories/{id}/imports` — List module import dependencies

### 4. Vector Embeddings & Knowledge Base
- `POST /api/v1/repositories/{id}/index` — Build vector embeddings index
- `GET /api/v1/repositories/{id}/index/stats` — Fetch vector index statistics
- `DELETE /api/v1/repositories/{id}/index` — Delete vector index

### 5. Multi-Modal Search
- `POST /api/v1/repositories/{id}/search` — Search code using `semantic`, `keyword`, `symbol`, or `rrf_hybrid` modes

### 6. Repository Chat & Grounded QA
- `POST /api/v1/repositories/{id}/chat/sessions` — Create chat session
- `GET /api/v1/repositories/{id}/chat/sessions` — List chat sessions
- `GET /api/v1/chat/sessions/{id}` — Get session details & message history
- `POST /api/v1/chat/sessions/{id}/messages` — Send prompt (supports SSE streaming)
- `DELETE /api/v1/chat/sessions/{id}` — Delete chat session

### 7. AI Task Planner & Code Suggestions
- `POST /api/v1/repositories/{id}/plans` — Generate AI task decomposition execution plan
- `GET /api/v1/repositories/{id}/plans` — List task execution plans
- `GET /api/v1/plans/{id}` — Get plan details and step diffs
- `POST /api/v1/repositories/{id}/suggest-code` — Generate targeted code edit suggestion diff

### 8. Auto Documentation Generation
- `POST /api/v1/repositories/{id}/docs/generate` — Synthesize README, Architecture, or API Reference docs
- `GET /api/v1/repositories/{id}/docs` — List generated documentation files
- `GET /api/v1/docs/{id}` — Fetch documentation details
- `PUT /api/v1/docs/{id}` — Update documentation content
- `DELETE /api/v1/docs/{id}` — Delete documentation file

---

## Project Structure

```
ForgeAI/
├── backend/                  # FastAPI Python Backend
│   ├── alembic/              # Database migration scripts (001 - 006)
│   ├── src/forgeai/
│   │   ├── api/v1/           # REST routers (health, repositories, chat, planner, docs)
│   │   ├── core/             # Middleware, logging, exceptions
│   │   ├── models/           # Async SQLAlchemy ORM models
│   │   ├── repositories/     # Data access layer (DAL)
│   │   ├── schemas/          # Pydantic v2 DTOs
│   │   └── services/         # Core engines (scanner, parser, search, chat, planner, docs, monitor)
│   └── tests/                # Automated pytest test suite (Phases 1 - 9)
├── frontend/                 # Next.js 14 TypeScript Frontend
│   └── src/
│       ├── app/
│       │   └── dashboard/    # Dashboard pages (Repositories, Chat, Planner, Docs, Code, Stats)
│       ├── lib/              # Axios API client functions
│       └── types/            # TypeScript DTO interfaces
├── docker-compose.yml        # Infrastructure setup (PostgreSQL 16 + pgvector, Redis 7)
└── README.md
```

---

## Development & Verification

### Running Automated Test Suite

```bash
# Backend pytest suite (35 tests across all 9 phases)
cd backend
uv run pytest -v
```

### Running Frontend Linter

```bash
# Next.js ESLint verification
cd frontend
npm run lint
```

---

## License

MIT
