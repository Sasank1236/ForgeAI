"""Phase 7 unit & integration tests for AI Task Planner & Code Suggestions.

Tests:
1. TaskPlan & PlanStep ORM models
2. PlanRepo CRUD operations
3. TaskPlannerService task decomposition flow
4. CodeSuggestionService diff generation
5. REST API planner & suggestion endpoints
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.models.plan import PlanStatus
from forgeai.models.repository import RepositoryStatus
from forgeai.repositories.plan_repo import PlanRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.schemas.plan import (
    CodeSuggestionRequest,
    PlanCreateRequest,
)
from forgeai.services.code_suggestion import CodeSuggestionService
from forgeai.services.task_planner import TaskPlannerService


@pytest.mark.asyncio
async def test_plan_repo_crud(db_session: AsyncSession) -> None:
    """Test PlanRepo task plan creation, adding steps, listing, updating, and deletion."""
    repo_repo = RepositoryRepo(db_session)
    plan_repo = PlanRepo(db_session)

    repository = await repo_repo.create(name="PlanRepoTest", root_path="/tmp/plantest")
    await db_session.commit()

    # Create plan
    plan = await plan_repo.create_plan(
        repository_id=repository.id,
        title="Test JWT Auth Migration",
        goal_description="Migrate basic auth to JWT refresh tokens",
        impact_summary="Moderate impact on authentication handlers",
    )
    await db_session.commit()

    assert plan.id is not None
    assert plan.title == "Test JWT Auth Migration"
    assert plan.status == PlanStatus.draft

    # Add steps
    step1 = await plan_repo.add_step(
        plan_id=plan.id,
        step_index=1,
        title="Add JWT Token Schema",
        description="Create token payload models",
        target_path="schemas/auth.py",
        code_diff="```diff\n+ class TokenPayload(BaseModel):\n```",
    )
    step2 = await plan_repo.add_step(
        plan_id=plan.id,
        step_index=2,
        title="Update Auth Route Handler",
        description="Integrate refresh token rotation",
        target_path="api/v1/auth.py",
    )
    await db_session.commit()

    assert step1.step_index == 1
    assert step2.step_index == 2

    # Fetch plan with preloaded steps
    fetched = await plan_repo.get_plan(plan.id)
    assert fetched is not None
    assert len(fetched.steps) == 2

    # List plans by repo
    plans = await plan_repo.list_plans_by_repo(repository.id)
    assert len(plans) == 1

    # Update plan status
    updated = await plan_repo.update_plan_status(plan.id, PlanStatus.completed)
    await db_session.commit()
    assert updated is not None
    assert updated.status == PlanStatus.completed

    # Delete plan
    deleted_count = await plan_repo.delete_plan(plan.id)
    await db_session.commit()
    assert deleted_count == 1


@pytest.mark.asyncio
async def test_task_planner_and_code_suggestion_services(db_session: AsyncSession) -> None:
    """Test TaskPlannerService and CodeSuggestionService execution."""
    repo_repo = RepositoryRepo(db_session)
    planner_svc = TaskPlannerService(db_session)
    suggestion_svc = CodeSuggestionService(db_session)

    repository = await repo_repo.create(name="PlannerSvcRepo", root_path="/tmp/plannersvc")
    await repo_repo.update_status(repository.id, RepositoryStatus.ready)
    await db_session.commit()

    # 1. Test TaskPlannerService.generate_plan
    plan_dto = await planner_svc.generate_plan(
        repository.id,
        PlanCreateRequest(
            goal_description="Add rate limiting middleware to FastAPI router",
            title="Rate Limiter Integration Plan",
        ),
    )
    assert plan_dto.id is not None
    assert plan_dto.title == "Rate Limiter Integration Plan"
    assert len(plan_dto.steps) >= 1

    # 2. Test CodeSuggestionService.generate_suggestion
    sugg_dto = await suggestion_svc.generate_suggestion(
        repository.id,
        CodeSuggestionRequest(
            file_path="src/main.py",
            instruction="Add redis rate limiting dependency",
        ),
    )
    assert sugg_dto.target_path == "src/main.py"
    assert "a/src/main.py" in sugg_dto.diff or "b/src/main.py" in sugg_dto.diff


@pytest.mark.asyncio
async def test_planner_api_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test Planner REST API endpoints (plans CRUD & code suggestion)."""
    repo_repo = RepositoryRepo(db_session)

    repository = await repo_repo.create(name="ApiPlannerRepo", root_path="/tmp/apiplanner")
    await repo_repo.update_status(repository.id, RepositoryStatus.ready)
    await db_session.commit()

    # 1. Generate Task Plan
    create_resp = await client.post(
        f"/api/v1/repositories/{repository.id}/plans",
        json={
            "goal_description": "Implement caching layer for symbol queries",
            "title": "Symbol Query Cache Plan",
        },
    )
    assert create_resp.status_code == 201
    plan_id = create_resp.json()["id"]

    # 2. List Plans
    list_resp = await client.get(f"/api/v1/repositories/{repository.id}/plans")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    # 3. Get Plan Details
    get_resp = await client.get(f"/api/v1/plans/{plan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Symbol Query Cache Plan"

    # 4. Generate Code Suggestion
    sugg_resp = await client.post(
        f"/api/v1/repositories/{repository.id}/suggest-code",
        json={
            "file_path": "services/symbol.py",
            "instruction": "Add TTL cache decorator to get_symbols query",
        },
    )
    assert sugg_resp.status_code == 200
    assert sugg_resp.json()["target_path"] == "services/symbol.py"

    # 5. Delete Plan
    del_resp = await client.delete(f"/api/v1/plans/{plan_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
