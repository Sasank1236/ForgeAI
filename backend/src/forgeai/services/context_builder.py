"""Grounded context builder service.

Stuffs retrieved multi-modal search hits into a structured, line-level cited prompt context
for LLM grounded code QA.

Phase 6 — Repository Chat & Grounded QA
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.schemas.chat import CitationItem
from forgeai.schemas.search import SearchQueryRequest, SearchType
from forgeai.services.search import SearchService

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT_TEMPLATE = """You are ForgeAI, an advanced AI software engineering assistant pair-programming with the user.
You have direct read-access to the user's codebase. Use the grounded code context below to answer questions with high technical precision.

Guidelines:
1. Ground your answer strictly in the provided repository context snippets whenever applicable.
2. Explicitly cite file paths and line ranges (e.g. `src/utils.py:L12-45`) when explaining code structure or logic.
3. Provide clean, production-ready code examples when requested.
4. If the provided context does not contain enough information to answer definitively, state what is known and what requires further verification.
"""


class ContextBuilderService:
    """Retrieves and packages grounded codebase context for chat prompts."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._search_service = SearchService(db)

    async def build_grounded_context(
        self,
        repo_id: UUID,
        user_query: str,
        search_type: str = "hybrid",
        max_chunks: int = 8,
        min_score: float = 0.0,
    ) -> tuple[str, list[CitationItem]]:
        """Retrieve relevant code chunks and format grounded prompt context + citations.

        Returns
        -------
        tuple[str, list[CitationItem]]
            Formated system context string and list of CitationItem DTOs.
        """
        try:
            stype = SearchType(search_type.lower())
        except ValueError:
            stype = SearchType.hybrid

        search_req = SearchQueryRequest(
            query=user_query,
            search_type=stype,
            limit=max_chunks,
            min_score=min_score,
        )

        search_res = await self._search_service.search(repo_id, search_req)
        hits = search_res.results

        citations: list[CitationItem] = []
        context_blocks: list[str] = []

        for hit in hits:
            citation = CitationItem(
                file_id=hit.file_id,
                relative_path=hit.relative_path,
                symbol_id=hit.symbol_id,
                name=hit.name,
                start_line=hit.start_line,
                end_line=hit.end_line,
                score=hit.score,
            )
            citations.append(citation)

            snippet_header = (
                f"--- CONTEXT BLOCK: {hit.relative_path} "
                f"(Lines {hit.start_line}-{hit.end_line}) | Match Score: {int(hit.score * 100)}% ---"
            )
            block_str = f"{snippet_header}\n{hit.chunk_text}"
            context_blocks.append(block_str)

        if context_blocks:
            grounded_section = (
                "\n\n=== GROUNDED REPOSITORY CONTEXT ===\n" + "\n\n".join(context_blocks) + "\n====================================="
            )
        else:
            grounded_section = "\n\n(No direct matching code snippets found in repository index for this query.)"

        full_system_context = SYSTEM_PROMPT_TEMPLATE + grounded_section

        logger.info(
            "grounded_context_built",
            repo_id=str(repo_id),
            query=user_query,
            chunks_count=len(citations),
        )

        return full_system_context, citations
