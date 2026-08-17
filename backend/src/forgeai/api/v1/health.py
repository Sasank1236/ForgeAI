"""Health check and system telemetry endpoints.

Routes
------
GET /api/v1/health          Basic liveness probe
GET /api/v1/health/system   Comprehensive system telemetry & readiness probe
"""

from __future__ import annotations

import redis.asyncio as redis
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.database import get_db
from forgeai.redis_client import get_redis
from forgeai.services.system_monitor import SystemMonitorService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="Health Check",
    description="Returns basic operational liveness status.",
    response_description="Basic health status",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis),
) -> dict[str, str]:
    """Check the health of core services."""
    db_status = "disconnected"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        logger.warning("health_check_db_failed", error=str(exc))

    redis_status = "disconnected"
    try:
        pong = await cache.ping()
        if pong:
            redis_status = "connected"
    except Exception as exc:
        logger.warning("health_check_redis_failed", error=str(exc))

    all_healthy = db_status == "connected" and redis_status == "connected"
    overall = "ok" if all_healthy else "degraded"

    return {
        "status": overall,
        "version": "1.0.0",
        "database": db_status,
        "cache": redis_status,
    }


@router.get(
    "/health/system",
    summary="System Telemetry & Monitoring",
    description="Returns detailed host metrics, disk usage, and database telemetry counts.",
)
async def system_telemetry(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch comprehensive system observability and database telemetry."""
    monitor = SystemMonitorService(db)
    return await monitor.get_system_health()
