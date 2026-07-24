"""Health check endpoint.

GET /api/v1/health
  Returns the operational status of the API, database, and cache.
  Used for liveness/readiness probes and monitoring dashboards.
"""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as redis

from forgeai.database import get_db
from forgeai.redis_client import get_redis

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="Health Check",
    description=(
        "Returns the health status of the API, database connection, "
        "and Redis cache. Useful for liveness and readiness probes."
    ),
    response_description="Service health status",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis),
) -> dict[str, str]:
    """Check the health of all dependent services."""
    # ─── Database check ───────────────────────────────────────────────────────
    db_status = "disconnected"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        logger.warning("health_check_db_failed", error=str(exc))

    # ─── Redis check ──────────────────────────────────────────────────────────
    redis_status = "disconnected"
    try:
        pong = await cache.ping()
        if pong:
            redis_status = "connected"
    except Exception as exc:
        logger.warning("health_check_redis_failed", error=str(exc))

    # ─── Overall status ───────────────────────────────────────────────────────
    all_healthy = db_status == "connected" and redis_status == "connected"
    overall = "ok" if all_healthy else "degraded"

    return {
        "status": overall,
        "version": "1.0.0",
        "database": db_status,
        "cache": redis_status,
    }
