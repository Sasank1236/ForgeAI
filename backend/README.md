# ForgeAI Backend

FastAPI backend for ForgeAI — Repository-Aware AI Coding Assistant.

See the [root README](../README.md) for full project documentation.

## Running locally

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn src.forgeai.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs
