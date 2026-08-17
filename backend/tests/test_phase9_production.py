"""Phase 9 unit & integration tests for Production Polish & System Monitoring.

Tests:
1. RequestLoggingMiddleware X-Request-ID correlation header injection
2. SystemMonitorService disk & database count telemetry
3. GET /api/v1/health liveness probe
4. GET /api/v1/health/system readiness probe & telemetry metrics
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.services.system_monitor import SystemMonitorService


@pytest.mark.asyncio
async def test_system_monitor_service(db_session: AsyncSession) -> None:
    """Test SystemMonitorService system health computation and database telemetry counts."""
    repo_repo = RepositoryRepo(db_session)
    await repo_repo.create(name="ProdMonitorTest", root_path="/tmp/prodmonitortest")
    await db_session.commit()

    monitor = SystemMonitorService(db_session)
    health_data = await monitor.get_system_health()

    assert health_data["status"] in ("ok", "degraded")
    assert "system" in health_data
    assert "disk_free_gb" in health_data["system"]
    assert "telemetry" in health_data
    assert health_data["telemetry"]["repositories"] >= 1


@pytest.mark.asyncio
async def test_middleware_request_id_header(client: AsyncClient) -> None:
    """Test RequestLoggingMiddleware X-Request-ID correlation header injection."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    assert "x-response-time" in resp.headers


@pytest.mark.asyncio
async def test_system_telemetry_endpoint(client: AsyncClient) -> None:
    """Test GET /api/v1/health/system REST API endpoint."""
    resp = await client.get("/api/v1/health/system")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "system" in data
    assert "telemetry" in data
