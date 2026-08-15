"""Task plan data-access layer.

Thin async SQLAlchemy queries for the task_plans and plan_steps tables.

Phase 7 — AI Task Planner & Code Suggestions
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forgeai.models.plan import PlanStatus, PlanStep, TaskPlan

logger = structlog.get_logger(__name__)


class PlanRepo:
    """CRUD operations for the ``task_plans`` and ``plan_steps`` tables."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_plan(
        self,
        repository_id: UUID,
        title: str,
        goal_description: str,
        impact_summary: str | None = None,
        status: PlanStatus = PlanStatus.draft,
    ) -> TaskPlan:
        """Create a new task execution plan."""
        plan = TaskPlan(
            repository_id=repository_id,
            title=title,
            goal_description=goal_description,
            impact_summary=impact_summary,
            status=status,
        )
        self._db.add(plan)
        await self._db.flush()
        logger.info(
            "task_plan_created",
            plan_id=str(plan.id),
            repo_id=str(repository_id),
            title=title,
        )
        return plan

    async def get_plan(self, plan_id: UUID) -> TaskPlan | None:
        """Fetch a single task plan by UUID with steps preloaded."""
        stmt = (
            select(TaskPlan)
            .options(selectinload(TaskPlan.steps))
            .where(TaskPlan.id == plan_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_plans_by_repo(self, repository_id: UUID) -> list[TaskPlan]:
        """Fetch all execution plans for a repository ordered by creation date."""
        stmt = (
            select(TaskPlan)
            .options(selectinload(TaskPlan.steps))
            .where(TaskPlan.repository_id == repository_id)
            .order_by(TaskPlan.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def add_step(
        self,
        plan_id: UUID,
        step_index: int,
        title: str,
        description: str,
        target_path: str,
        code_diff: str | None = None,
        status: PlanStatus = PlanStatus.draft,
    ) -> PlanStep:
        """Add an execution step to a task plan."""
        step = PlanStep(
            plan_id=plan_id,
            step_index=step_index,
            title=title,
            description=description,
            target_path=target_path,
            code_diff=code_diff,
            status=status,
        )
        self._db.add(step)
        await self._db.flush()
        return step

    async def update_plan_status(
        self,
        plan_id: UUID,
        status: PlanStatus,
    ) -> TaskPlan | None:
        """Update status of a task plan."""
        plan = await self.get_plan(plan_id)
        if plan:
            plan.status = status
            await self._db.flush()
        return plan

    async def delete_plan(self, plan_id: UUID) -> int:
        """Delete a task plan and its steps."""
        stmt = delete(TaskPlan).where(TaskPlan.id == plan_id)
        result = await self._db.execute(stmt)
        return result.rowcount
