"""Pydantic DTOs for the code symbol API.

Request/response schemas for symbol endpoints:
  - SymbolResponse: full symbol record
  - SymbolListResponse: paginated list of symbols
  - SymbolFilter: query parameters for filtering symbols

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from forgeai.models.symbol import SymbolType, Visibility


# ── Response ──────────────────────────────────────────────────────────────────

class SymbolResponse(BaseModel):
    """Full symbol record returned by the API."""

    id: UUID
    repository_id: UUID
    file_id: UUID
    name: str
    symbol_type: SymbolType
    language: str
    parent_symbol_id: UUID | None = None

    # Position
    start_line: int = Field(..., description="1-based line where the symbol starts.")
    end_line: int = Field(..., description="1-based line where the symbol ends.")
    start_column: int = Field(
        0, description="0-based column where the symbol starts."
    )
    end_column: int = Field(
        0, description="0-based column where the symbol ends."
    )

    # Metadata
    visibility: Visibility | None = None
    signature: str | None = None
    docstring: str | None = None

    model_config = {"from_attributes": True}


class SymbolListResponse(BaseModel):
    """Paginated list of symbols for a repository."""

    items: list[SymbolResponse]
    total: int
    page: int
    page_size: int


# ── Filter ────────────────────────────────────────────────────────────────────

class SymbolFilter(BaseModel):
    """Query-parameter filters for GET /api/v1/repositories/{id}/symbols."""

    symbol_type: SymbolType | None = Field(
        None,
        description="Filter symbols by type (function, class, method, …).",
    )
    language: str | None = Field(
        None,
        description="Filter symbols by language (e.g. 'Python', 'TypeScript').",
    )
    file_id: UUID | None = Field(
        None,
        description="Return only symbols belonging to this file.",
    )
    parent_symbol_id: UUID | None = Field(
        None,
        description="Return only direct children of this symbol.",
    )
    visibility: Visibility | None = Field(
        None,
        description="Filter by visibility modifier.",
    )
    name_contains: str | None = Field(
        None,
        description="Case-insensitive substring match on symbol name.",
    )
    page: int = Field(1, ge=1, description="Page number (1-indexed).")
    page_size: int = Field(50, ge=1, le=200, description="Items per page.")
