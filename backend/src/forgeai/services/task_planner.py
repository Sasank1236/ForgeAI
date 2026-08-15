"""AI Task Planner service.

Decomposes high-level engineering feature requests and refactoring goals into
structured multi-step execution plans with file targets and code diff suggestions.

Phase 7 — AI Task Planner & Code Suggestions
"""

from __future__ import annotations

import json
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.config import get_settings
from forgeai.models.plan import PlanStatus
from forgeai.repositories.plan_repo import PlanRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.schemas.plan import (
    PlanCreateRequest,
    PlanStepResponse,
    TaskPlanListResponse,
    TaskPlanResponse,
)
from forgeai.schemas.search import SearchQueryRequest, SearchType
from forgeai.services.search import SearchService

logger = structlog.get_logger(__name__)


PLANNER_SYSTEM_PROMPT = """You are ForgeAI, an expert AI Software Architect.
Decompose the user's high-level engineering goal into a structured multi-step execution plan.

Your response MUST be valid JSON in the following format:
{
  "title": "Short descriptive title of the plan",
  "impact_summary": "Architectural risk and impact summary (1-2 sentences)",
  "steps": [
    {
      "step_index": 1,
      "title": "Step title",
      "description": "Clear explanation of work to perform",
      "target_path": "relative/file/path.py",
      "code_diff": "```diff\\n- old_code()\\n+ new_code()\\n```"
    }
  ]
}
"""


class TaskPlannerService:
    """Service orchestrating AI task decomposition into step-by-step plans."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._plan_repo = PlanRepo(db)
        self._repo_repo = RepositoryRepo(db)
        self._search_service = SearchService(db)
        self._settings = get_settings()

    async def generate_plan(
        self,
        repository_id: UUID,
        request: PlanCreateRequest,
    ) -> TaskPlanResponse:
        """Analyze repository context and generate a multi-step task execution plan."""
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository {repository_id} not found.")

        # 1. Search relevant codebase context
        search_res = await self._search_service.search(
            repository_id,
            SearchQueryRequest(
                query=request.goal_description,
                search_type=SearchType.hybrid,
                limit=6,
            ),
        )

        context_paths = [r.relative_path for r in search_res.results]

        # 2. Invoke LLM or generate structured plan
        plan_data = await self._llm_decompose_goal(
            goal=request.goal_description,
            custom_title=request.title,
            context_hits=search_res.results,
        )

        # 3. Save plan to DB
        plan = await self._plan_repo.create_plan(
            repository_id=repository_id,
            title=plan_data.get("title", request.title or "Engineering Execution Plan"),
            goal_description=request.goal_description,
            impact_summary=plan_data.get("impact_summary"),
            status=PlanStatus.draft,
        )

        steps_dto: list[PlanStepResponse] = []
        for step_dict in plan_data.get("steps", []):
            step_orm = await self._plan_repo.add_step(
                plan_id=plan.id,
                step_index=step_dict.get("step_index", len(steps_dto) + 1),
                title=step_dict.get("title", f"Step {len(steps_dto) + 1}"),
                description=step_dict.get("description", "Execute step implementation."),
                target_path=step_dict.get("target_path", context_paths[0] if context_paths else "src/main.py"),
                code_diff=step_dict.get("code_diff"),
                status=PlanStatus.draft,
            )
            steps_dto.append(
                PlanStepResponse(
                    id=step_orm.id,
                    plan_id=plan.id,
                    step_index=step_orm.step_index,
                    title=step_orm.title,
                    description=step_orm.description,
                    target_path=step_orm.target_path,
                    code_diff=step_orm.code_diff,
                    status=step_orm.status,
                    created_at=step_orm.created_at,
                )
            )

        await self._db.commit()

        logger.info(
            "task_plan_generated",
            plan_id=str(plan.id),
            repo_id=str(repository_id),
            steps_count=len(steps_dto),
        )

        return TaskPlanResponse(
            id=plan.id,
            repository_id=plan.repository_id,
            title=plan.title,
            goal_description=plan.goal_description,
            status=plan.status,
            impact_summary=plan.impact_summary,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            steps=steps_dto,
        )

    async def list_plans(self, repository_id: UUID) -> TaskPlanListResponse:
        """List all execution plans for a repository."""
        plans_orm = await self._plan_repo.list_plans_by_repo(repository_id)
        items: list[TaskPlanResponse] = []
        for p in plans_orm:
            steps_dto = [
                PlanStepResponse(
                    id=s.id,
                    plan_id=s.plan_id,
                    step_index=s.step_index,
                    title=s.title,
                    description=s.description,
                    target_path=s.target_path,
                    code_diff=s.code_diff,
                    status=s.status,
                    created_at=s.created_at,
                )
                for s in p.steps
            ]
            items.append(
                TaskPlanResponse(
                    id=p.id,
                    repository_id=p.repository_id,
                    title=p.title,
                    goal_description=p.goal_description,
                    status=p.status,
                    impact_summary=p.impact_summary,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    steps=steps_dto,
                )
            )
        return TaskPlanListResponse(items=items, total=len(items))

    async def get_plan(self, plan_id: UUID) -> TaskPlanResponse:
        """Fetch plan by UUID with steps."""
        plan = await self._plan_repo.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Task plan {plan_id} not found.")

        steps_dto = [
            PlanStepResponse(
                id=s.id,
                plan_id=s.plan_id,
                step_index=s.step_index,
                title=s.title,
                description=s.description,
                target_path=s.target_path,
                code_diff=s.code_diff,
                status=s.status,
                created_at=s.created_at,
            )
            for s in plan.steps
        ]
        return TaskPlanResponse(
            id=plan.id,
            repository_id=plan.repository_id,
            title=plan.title,
            goal_description=plan.goal_description,
            status=plan.status,
            impact_summary=plan.impact_summary,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            steps=steps_dto,
        )

    async def delete_plan(self, plan_id: UUID) -> bool:
        """Delete an execution plan."""
        deleted = await self._plan_repo.delete_plan(plan_id)
        await self._db.commit()
        return deleted > 0

    async def _llm_decompose_goal(
        self,
        goal: str,
        custom_title: str | None,
        context_hits: list,
    ) -> dict:
        """Call LiteLLM or OpenAI, fallback to structured mock decomposition."""
        api_key = getattr(self._settings, "openai_api_key", "")
        if api_key:
            try:
                import litellm

                context_summary = "\n".join(
                    [f"- {h.relative_path} (Lines {h.start_line}-{h.end_line})" for h in context_hits]
                )
                prompt = (
                    f"User Engineering Goal: {goal}\n\n"
                    f"Relevant Code Files:\n{context_summary}\n\n"
                    "Decompose this task into 2-4 logical implementation steps."
                )

                res = await litellm.acompletion(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    api_key=api_key,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                content = res.choices[0].message.content or "{}"
                return json.loads(content)
            except Exception as exc:
                logger.warning("planner_llm_failed_using_fallback", error=str(exc))

        # Fallback structured decomposition generator
        target1 = context_hits[0].relative_path if context_hits else "src/main.py"
        target2 = context_hits[1].relative_path if len(context_hits) > 1 else target1

        return {
            "title": custom_title or f"Plan: {goal[:40].strip()}...",
            "impact_summary": f"Modifies core logic in {target1}. Moderate architectural impact with low backward-compatibility risk.",
            "steps": [
                {
                    "step_index": 1,
                    "title": "Define Interfaces & Models",
                    "description": f"Add required data structures and state variables in `{target1}`.",
                    "target_path": target1,
                    "code_diff": f"```diff\n--- a/{target1}\n+++ b/{target1}\n@@ -10,6 +10,12 @@\n+# Added for {goal[:30]}\n+class FeatureConfig:\n+    enabled: bool = True\n```",
                },
                {
                    "step_index": 2,
                    "title": "Implement Core Logic",
                    "description": f"Integrate feature logic into handlers and services in `{target2}`.",
                    "target_path": target2,
                    "code_diff": f"```diff\n--- a/{target2}\n+++ b/{target2}\n@@ -45,4 +45,8 @@\n async def process_request():\n-    return True\n+    # Execute feature step\n+    return await execute_feature()\n```",
                },
            ],
        }
