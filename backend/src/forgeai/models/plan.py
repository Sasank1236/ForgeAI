"""Task plan & plan step ORM models.

Database tables for storing AI-generated task decomposition execution plans,
target file steps, and code diff suggestions.

Phase 7 — AI Task Planner & Code Suggestions
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from forgeai.database import Base


class PlanStatus(enum.StrEnum):
    """Execution status of a task plan or plan step."""

    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class TaskPlan(Base):
    """ORM model representing an AI execution plan for a repository feature/refactoring."""

    __tablename__ = "task_plans"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    repository_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    goal_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus, name="plan_status_enum", native_enum=False),
        nullable=False,
        default=PlanStatus.draft,
    )
    impact_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    steps: Mapped[list[PlanStep]] = relationship(
        "PlanStep",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanStep.step_index",
    )

    def __repr__(self) -> str:
        return f"<TaskPlan id={self.id} title='{self.title}' status={self.status}>"


class PlanStep(Base):
    """ORM model representing a single step within an execution plan."""

    __tablename__ = "plan_steps"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("task_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    target_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    code_diff: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus, name="plan_step_status_enum", native_enum=False),
        nullable=False,
        default=PlanStatus.draft,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Relationships
    plan: Mapped[TaskPlan] = relationship(
        "TaskPlan",
        back_populates="steps",
    )

    def __repr__(self) -> str:
        return f"<PlanStep id={self.id} plan_id={self.plan_id} step={self.step_index} target={self.target_path}>"
