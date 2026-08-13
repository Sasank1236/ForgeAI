"""Repository search Pydantic DTO schemas.

Phase 5 — Repository Search (Semantic + Hybrid)
"""

from __future__ import annotations

import enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchType(enum.StrEnum):
    """Kinds of search operations supported by ForgeAI."""

    hybrid = "hybrid"
    semantic = "semantic"
    keyword = "keyword"
    symbol = "symbol"


class SearchQueryRequest(BaseModel):
    """Request payload for repository code search."""

    query: str = Field(
        min_length=1,
        description="Search query string (natural language question, code snippet, or symbol name).",
    )
    search_type: SearchType = Field(
        default=SearchType.hybrid,
        description="Search modality: 'hybrid' (RRF fusion), 'semantic' (vector AI), 'keyword' (FTS/text), 'symbol'.",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of search results to return.",
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum score threshold for inclusion.",
    )
    language: str | None = Field(
        default=None,
        description="Optional filter by language (e.g. 'Python', 'TypeScript').",
    )
    extension: str | None = Field(
        default=None,
        description="Optional filter by file extension (e.g. '.py', '.ts').",
    )


class SearchResultItem(BaseModel):
    """Single matching hit in repository search results."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_id: UUID
    relative_path: str
    symbol_id: UUID | None = None
    name: str | None = None
    chunk_text: str
    chunk_type: str = "window"
    start_line: int = 1
    end_line: int = 1
    score: float = Field(
        ge=0.0,
        description="Relevance or similarity score.",
    )
    match_type: str = Field(
        description="Source match type ('semantic', 'keyword', 'symbol', or 'hybrid').",
    )


class SearchResponse(BaseModel):
    """API response wrapper for code search results."""

    query: str
    search_type: str
    total_hits: int
    duration_ms: int
    results: list[SearchResultItem]
