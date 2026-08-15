"""Task planner & code suggestions Pydantic DTO schemas.

Phase 7 — AI Task Planner & Code Suggestions
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from forgeai.models.plan import PlanStatus


class PlanCreateRequest(BaseModel):
    """Payload to create an AI task decomposition execution plan."""

    goal_description: str = Field(
        min_length=5,
        description="High-level engineering task or refactoring goal description.",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Optional custom title for the execution plan.",
    )


class PlanStepResponse(BaseModel):
    """API response DTO representing a single step within a task plan."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    step_index: int
    title: str
    description: str
    target_path: str
    code_diff: str | None = None
    status: PlanStatus
    created_at: datetime


class TaskPlanResponse(BaseModel):
    """API response DTO representing a full task decomposition execution plan."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    title: str
    goal_description: str
    status: PlanStatus
    impact_summary: str | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[PlanStepResponse] = Field(default_factory=list)


class TaskPlanListResponse(BaseModel):
    """Paginated list response wrapper for task plans."""

    items: list[TaskPlanResponse]
    total: int


class CodeSuggestionRequest(BaseModel):
    """Payload to generate an AI code edit/diff suggestion for a file."""

    file_path: str = Field(
        min_length=1,
        description="Relative file path within the repository.",
    )
    instruction: str = Field(
        min_length=3,
        description="Specific instruction or refactoring request for the file.",
    )
    context_lines: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of context lines surrounding the edit.",
    )


class CodeSuggestionResponse(BaseModel):
    """API response DTO representing an AI code suggestion diff."""

    target_path: str
    original_snippet: str
    suggested_snippet: str
    diff: str
    explanation: str
