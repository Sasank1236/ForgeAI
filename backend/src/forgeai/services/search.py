"""Multi-modal codebase search service.

Implements Semantic vector search, Keyword text search, Symbol search, and
Reciprocal Rank Fusion (RRF) Hybrid search over repository codebases.

Phase 5 — Repository Search (Semantic + Hybrid)
"""

from __future__ import annotations

import time
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.repositories.symbol_repo import SymbolRepo
from forgeai.schemas.search import (
    SearchQueryRequest,
    SearchResponse,
    SearchResultItem,
    SearchType,
)
from forgeai.services.knowledge_base import KnowledgeBaseService

logger = structlog.get_logger(__name__)


class SearchService:
    """Multi-modal search engine for codebases."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = RepositoryRepo(db)
        self._file_repo = FileRepo(db)
        self._symbol_repo = SymbolRepo(db)
        self._kb_service = KnowledgeBaseService(db)

    async def search(
        self,
        repo_id: UUID,
        request: SearchQueryRequest,
    ) -> SearchResponse:
        """Unified search dispatcher."""
        start_time = time.perf_counter()

        repository = await self._repo.get_by_id(repo_id)
        if repository is None:
            raise ValueError(f"Repository {repo_id} not found.")

        search_type = request.search_type

        if search_type == SearchType.semantic:
            hits = await self.search_semantic(repo_id, request)
        elif search_type == SearchType.keyword:
            hits = await self.search_keyword(repo_id, request)
        elif search_type == SearchType.symbol:
            hits = await self.search_symbol(repo_id, request)
        else:
            hits = await self.search_hybrid(repo_id, request)

        # Filter by language or extension if requested
        if request.language:
            target_lang = request.language.lower()
            hits = [
                h for h in hits if h.relative_path.lower().endswith(target_lang) or target_lang in h.relative_path.lower()
            ]
        if request.extension:
            ext = request.extension.lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            hits = [h for h in hits if h.relative_path.lower().endswith(ext)]

        # Filter by min_score threshold
        if request.min_score > 0.0:
            hits = [h for h in hits if h.score >= request.min_score]

        # Enforce max limit
        hits = hits[: request.limit]
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "search_executed",
            repo_id=str(repo_id),
            search_type=search_type.value,
            query=request.query,
            total_hits=len(hits),
            duration_ms=duration_ms,
        )

        return SearchResponse(
            query=request.query,
            search_type=search_type.value,
            total_hits=len(hits),
            duration_ms=duration_ms,
            results=hits,
        )

    async def search_semantic(
        self,
        repo_id: UUID,
        request: SearchQueryRequest,
    ) -> list[SearchResultItem]:
        """Perform semantic vector similarity search via KnowledgeBaseService."""
        vector_results = await self._kb_service.search_similar(
            repo_id=repo_id,
            query=request.query,
            limit=request.limit * 2,
            min_similarity=request.min_score,
        )

        items: list[SearchResultItem] = []
        for r in vector_results:
            items.append(
                SearchResultItem(
                    id=r.id,
                    file_id=r.file_id,
                    relative_path=r.relative_path,
                    symbol_id=r.symbol_id,
                    chunk_text=r.chunk_text,
                    chunk_type=r.chunk_type,
                    start_line=r.start_line,
                    end_line=r.end_line,
                    score=round(r.similarity, 4),
                    match_type="semantic",
                )
            )
        return items

    async def search_keyword(
        self,
        repo_id: UUID,
        request: SearchQueryRequest,
    ) -> list[SearchResultItem]:
        """Perform text/keyword search over repository files."""
        query_terms = [t.lower() for t in request.query.split() if len(t) > 1]
        if not query_terms:
            query_terms = [request.query.lower()]

        files, _ = await self._file_repo.list_by_repo(repo_id, page=1, page_size=2000)
        items: list[SearchResultItem] = []

        for file in files:
            if file.is_binary:
                continue

            path_match_score = 0.0
            file_path_lower = file.relative_path.lower()
            for term in query_terms:
                if term in file_path_lower:
                    path_match_score += 0.5

            abs_path = Path(file.absolute_path)
            if not abs_path.is_file():
                continue

            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lines = content.splitlines()
            for line_no, line_str in enumerate(lines, start=1):
                line_lower = line_str.lower()
                matches = sum(1 for term in query_terms if term in line_lower)
                if matches > 0:
                    score = min(1.0, 0.4 * matches + path_match_score)
                    # Excerpt context (+/- 2 lines)
                    ctx_start = max(0, line_no - 3)
                    ctx_end = min(len(lines), line_no + 2)
                    snippet = "\n".join(lines[ctx_start:ctx_end])

                    items.append(
                        SearchResultItem(
                            id=file.id,
                            file_id=file.id,
                            relative_path=file.relative_path,
                            chunk_text=f"// Match in {file.relative_path}:{line_no}\n{snippet}",
                            chunk_type="keyword",
                            start_line=line_no,
                            end_line=min(len(lines), line_no + 3),
                            score=round(score, 4),
                            match_type="keyword",
                        )
                    )
                    if len(items) >= request.limit * 3:
                        break

        items.sort(key=lambda x: x.score, reverse=True)
        return items

    async def search_symbol(
        self,
        repo_id: UUID,
        request: SearchQueryRequest,
    ) -> list[SearchResultItem]:
        """Perform symbol name search via SymbolRepo."""
        symbols, _ = await self._symbol_repo.list_by_repo(
            repo_id,
            name_query=request.query,
            page=1,
            page_size=request.limit * 2,
        )

        items: list[SearchResultItem] = []
        for sym in symbols:
            # Calculate simple string matching relevance
            name_lower = sym.name.lower()
            q_lower = request.query.lower()
            if name_lower == q_lower:
                score = 1.0
            elif name_lower.startswith(q_lower):
                score = 0.85
            else:
                score = 0.65

            file_record = await self._file_repo.get_by_id(sym.file_id)
            rel_path = file_record.relative_path if file_record else "unknown"

            header = f"// Symbol: {sym.symbol_type.value} {sym.name} in {rel_path}:{sym.start_line}"
            if sym.signature:
                header += f"\n// Signature: {sym.signature}"
            if sym.docstring:
                header += f"\n// Docstring: {sym.docstring[:150]}"

            items.append(
                SearchResultItem(
                    id=sym.id,
                    file_id=sym.file_id,
                    relative_path=rel_path,
                    symbol_id=sym.id,
                    name=sym.name,
                    chunk_text=header,
                    chunk_type="symbol",
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    score=round(score, 4),
                    match_type="symbol",
                )
            )

        items.sort(key=lambda x: x.score, reverse=True)
        return items

    async def search_hybrid(
        self,
        repo_id: UUID,
        request: SearchQueryRequest,
    ) -> list[SearchResultItem]:
        """Perform Reciprocal Rank Fusion (RRF) Hybrid Search.

        Combines Semantic, Keyword, and Symbol search results:
        RRF_Score = 1/(60 + rank_semantic) + 1/(60 + rank_keyword) + 1/(60 + rank_symbol)
        """
        # Fetch candidate pools from all 3 modalities
        semantic_hits = await self.search_semantic(repo_id, request)
        keyword_hits = await self.search_keyword(repo_id, request)
        symbol_hits = await self.search_symbol(repo_id, request)

        rrf_k = 60.0
        scores: dict[str, float] = {}
        item_map: dict[str, SearchResultItem] = {}

        # 1. Semantic RRF scoring
        for rank, item in enumerate(semantic_hits, start=1):
            key = f"{item.file_id}:{item.start_line}"
            rrf_contrib = 1.0 / (rrf_k + rank)
            scores[key] = scores.get(key, 0.0) + rrf_contrib
            item_map[key] = item

        # 2. Keyword RRF scoring
        for rank, item in enumerate(keyword_hits, start=1):
            key = f"{item.file_id}:{item.start_line}"
            rrf_contrib = 1.0 / (rrf_k + rank)
            scores[key] = scores.get(key, 0.0) + rrf_contrib
            if key not in item_map:
                item_map[key] = item

        # 3. Symbol RRF scoring
        for rank, item in enumerate(symbol_hits, start=1):
            key = f"{item.file_id}:{item.start_line}"
            rrf_contrib = 1.0 / (rrf_k + rank)
            scores[key] = scores.get(key, 0.0) + (rrf_contrib * 1.2)   # Slightly boost symbol matches
            if key not in item_map:
                item_map[key] = item

        if not scores:
            return []

        # Normalize RRF scores relative to max score
        max_rrf = max(scores.values())

        fused_items: list[SearchResultItem] = []
        for key, raw_rrf in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
            orig_item = item_map[key]
            norm_score = round(raw_rrf / max_rrf, 4)

            fused_items.append(
                SearchResultItem(
                    id=orig_item.id,
                    file_id=orig_item.file_id,
                    relative_path=orig_item.relative_path,
                    symbol_id=orig_item.symbol_id,
                    name=orig_item.name,
                    chunk_text=orig_item.chunk_text,
                    chunk_type=orig_item.chunk_type,
                    start_line=orig_item.start_line,
                    end_line=orig_item.end_line,
                    score=norm_score,
                    match_type="hybrid",
                )
            )

        return fused_items
