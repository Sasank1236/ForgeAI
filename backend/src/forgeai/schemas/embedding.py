"""Embedding & Knowledge Base Pydantic DTO schemas.

Phase 4 — Vector Embeddings & Knowledge Base
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IndexRequest(BaseModel):
    """Request payload to trigger vector embedding indexing for a repository."""

    force_reindex: bool = Field(
        default=False,
        description="Whether to clear existing vector index and perform full re-indexing.",
    )
    chunk_size: int = Field(
        default=512,
        ge=64,
        le=2048,
        description="Target maximum token count per chunk.",
    )
    overlap: int = Field(
        default=64,
        ge=0,
        le=512,
        description="Token overlap between consecutive sliding window chunks.",
    )
    languages: list[str] | None = Field(
        default=None,
        description="Optional subset of languages to index (e.g. ['Python', 'TypeScript']).",
    )


class ChunkInfo(BaseModel):
    """Metadata details for a single extracted code chunk."""

    model_config = ConfigDict(from_attributes=True)

    chunk_index: int
    chunk_type: str
    start_line: int
    end_line: int
    token_count: int


class IndexStatsResponse(BaseModel):
    """Execution statistics for a repository vector indexing job."""

    total_chunks: int = Field(default=0)
    total_embedded_files: int = Field(default=0)
    total_tokens: int = Field(default=0)
    duration_ms: int = Field(default=0)
    by_chunk_type: dict[str, int] = Field(default_factory=dict)


class IndexResponse(BaseModel):
    """API response after completing a vector indexing operation."""

    repository_id: UUID
    status: str
    stats: IndexStatsResponse


class EmbeddingSearchResult(BaseModel):
    """Single vector similarity search hit result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    file_id: UUID
    relative_path: str
    symbol_id: UUID | None = None
    chunk_index: int
    chunk_type: str
    chunk_text: str
    start_line: int
    end_line: int
    token_count: int
    similarity: float = Field(
        ge=0.0,
        le=1.0,
        description="Cosine similarity score (0.0 = orthogonal/opposite, 1.0 = identical).",
    )
