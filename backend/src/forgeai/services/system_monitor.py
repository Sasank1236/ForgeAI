"""System observability & telemetry service.

Provides real-time health checks, DB & Redis connection status, disk usage metrics,
and repository data telemetry using Python standard library.

Phase 9 — Production Polish, Security & Deployment
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from typing import Any

import redis.asyncio as redis
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.config import get_settings
from forgeai.models.chat import ChatSession
from forgeai.models.documentation import Documentation
from forgeai.models.embedding import CodeEmbedding
from forgeai.models.file import RepositoryFile
from forgeai.models.plan import TaskPlan
from forgeai.models.repository import Repository
from forgeai.models.symbol import Symbol
from forgeai.redis_client import _get_pool

logger = structlog.get_logger(__name__)


class SystemMonitorService:
    """Service providing real-time system metrics, readiness probes, and database telemetry."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._settings = get_settings()

    async def get_system_health(self) -> dict[str, Any]:
        """Compute full system health, resource utilization, and database counts."""
        db_status = "healthy"
        try:
            await self._db.execute(select(1))
        except Exception as exc:
            db_status = f"unhealthy: {exc}"

        redis_status = "disconnected"
        try:
            r_client = redis.Redis(connection_pool=_get_pool())
            if await r_client.ping():
                redis_status = "connected"
            await r_client.aclose()
        except Exception:
            redis_status = "unavailable"

        # Disk metrics using standard library shutil
        disk_usage = shutil.disk_usage(".")
        disk_free_gb = round(disk_usage.free / (1024**3), 2)
        disk_total_gb = round(disk_usage.total / (1024**3), 2)
        disk_percent = round((disk_usage.used / disk_usage.total) * 100, 1)

        # Database telemetry counts
        counts = await self._fetch_db_counts()

        overall_status = "ok" if db_status == "healthy" else "degraded"

        return {
            "status": overall_status,
            "environment": self._settings.app_env,
            "debug": self._settings.app_debug,
            "python_version": sys.version.split()[0],
            "database": db_status,
            "redis": redis_status,
            "system": {
                "pid": os.getpid(),
                "uptime_timestamp": time.time(),
                "disk_free_gb": disk_free_gb,
                "disk_total_gb": disk_total_gb,
                "disk_used_percent": disk_percent,
            },
            "telemetry": counts,
        }

    async def _fetch_db_counts(self) -> dict[str, int]:
        """Fetch total record counts across all core tables."""
        try:
            repo_c = await self._db.scalar(select(func.count(Repository.id))) or 0
            file_c = await self._db.scalar(select(func.count(RepositoryFile.id))) or 0
            symbol_c = await self._db.scalar(select(func.count(Symbol.id))) or 0
            embedding_c = await self._db.scalar(select(func.count(CodeEmbedding.id))) or 0
            chat_c = await self._db.scalar(select(func.count(ChatSession.id))) or 0
            plan_c = await self._db.scalar(select(func.count(TaskPlan.id))) or 0
            doc_c = await self._db.scalar(select(func.count(Documentation.id))) or 0

            return {
                "repositories": repo_c,
                "files": file_c,
                "symbols": symbol_c,
                "embeddings": embedding_c,
                "chat_sessions": chat_c,
                "task_plans": plan_c,
                "documentation_files": doc_c,
            }
        except Exception as exc:
            logger.warning("fetch_db_counts_failed", error=str(exc))
            return {
                "repositories": 0,
                "files": 0,
                "symbols": 0,
                "embeddings": 0,
                "chat_sessions": 0,
                "task_plans": 0,
                "documentation_files": 0,
            }
