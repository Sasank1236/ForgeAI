"""ForgeAI FastAPI application entry point.

Defines the app instance, middleware, lifespan, and router registration.
Run with: uvicorn src.forgeai.main:app --reload
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forgeai.api.v1 import chat, documentation, health, planner, repositories
from forgeai.config import get_settings
from forgeai.core.logging import configure_logging
from forgeai.redis_client import close_redis_pool

settings = get_settings()
configure_logging(debug=settings.app_debug)
logger = structlog.get_logger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    logger.info(
        "forgeai_starting",
        env=settings.app_env,
        debug=settings.app_debug,
    )
    yield
    logger.info("forgeai_shutting_down")
    await close_redis_pool()


# ─── Application ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="ForgeAI",
    description=(
        "Repository-Aware AI Coding Assistant. "
        "Understands your codebase before helping you write code."
    ),
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ─── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(repositories.router, prefix="/api/v1", tags=["Repositories"])
app.include_router(chat.router, prefix="/api/v1", tags=["Repository Chat"])
app.include_router(planner.router, prefix="/api/v1", tags=["AI Task Planner"])
app.include_router(documentation.router, prefix="/api/v1", tags=["Auto Documentation"])
