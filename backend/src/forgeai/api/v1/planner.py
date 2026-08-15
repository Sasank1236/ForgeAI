"""AI Task Planner & Code Suggestion API endpoints.

Routes
------
POST   /api/v1/repositories/{repo_id}/plans          Generate an AI execution plan
GET    /api/v1/repositories/{repo_id}/plans          List plans for repository
GET    /api/v1/plans/{plan_id}                        Get plan details with steps
DELETE /api/v1/plans/{plan_id}                        Delete plan
POST   /api/v1/repositories/{repo_id}/suggest-code   Generate code suggestion diff

Phase 7 — AI Task Planner & Code Suggestions
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.database import get_db
from forgeai.schemas.plan import (
    CodeSuggestionRequest,
    CodeSuggestionResponse,
    PlanCreateRequest,
    TaskPlanListResponse,
    TaskPlanResponse,
)
from forgeai.services.code_suggestion import CodeSuggestionService
from forgeai.services.task_planner import TaskPlannerService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["AI Task Planner"])


@router.post(
    "/repositories/{repo_id}/plans",
    response_model=TaskPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an AI task decomposition execution plan",
)
async def generate_task_plan(
    repo_id: uuid.UUID,
    body: PlanCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> TaskPlanResponse:
    """Decompose high-level engineering goal into a multi-step execution plan."""
    planner_svc = TaskPlannerService(db)
    try:
        return await planner_svc.generate_plan(repo_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/repositories/{repo_id}/plans",
    response_model=TaskPlanListResponse,
    summary="List task plans for a repository",
)
async def list_task_plans(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TaskPlanListResponse:
    """Fetch all execution plans generated for a repository."""
    planner_svc = TaskPlannerService(db)
    return await planner_svc.list_plans(repo_id)


@router.get(
    "/plans/{plan_id}",
    response_model=TaskPlanResponse,
    summary="Get task plan details and steps",
)
async def get_task_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TaskPlanResponse:
    """Fetch task plan details and step-by-step diffs."""
    planner_svc = TaskPlannerService(db)
    try:
        return await planner_svc.get_plan(plan_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/plans/{plan_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a task plan",
)
async def delete_task_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Delete a task plan."""
    planner_svc = TaskPlannerService(db)
    success = await planner_svc.delete_plan(plan_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task plan {plan_id} not found.",
        )
    return {"deleted": True}


@router.post(
    "/repositories/{repo_id}/suggest-code",
    response_model=CodeSuggestionResponse,
    summary="Generate targeted code suggestion diff",
)
async def generate_code_suggestion(
    repo_id: uuid.UUID,
    body: CodeSuggestionRequest,
    db: AsyncSession = Depends(get_db),
) -> CodeSuggestionResponse:
    """Generate targeted code edit suggestion diff for a file."""
    suggestion_svc = CodeSuggestionService(db)
    try:
        return await suggestion_svc.generate_suggestion(repo_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
