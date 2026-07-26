"""Pydantic DTOs for the import/dependency API.

Request/response schemas for import endpoints:
  - ImportRecordResponse: full import record
  - ImportListResponse: paginated list of imports
  - ImportFilter: query parameters for filtering imports

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from forgeai.models.import_ import ImportType


# ── Response ──────────────────────────────────────────────────────────────────

class ImportRecordResponse(BaseModel):
    """Full import record returned by the API.

    Named ``ImportRecordResponse`` (not ``ImportResponse``) to avoid collision
    with the Phase-2 ``ImportResponse`` (repository import operation).
    """

    id: UUID
    repository_id: UUID
    file_id: UUID
    source_symbol: str | None = None
    target_module: str
    import_type: ImportType
    alias: str | None = None

    model_config = {"from_attributes": True}


class ImportListResponse(BaseModel):
    """Paginated list of imports for a repository."""

    items: list[ImportRecordResponse]
    total: int
    page: int
    page_size: int


# ── Filter ────────────────────────────────────────────────────────────────────

class ImportFilter(BaseModel):
    """Query-parameter filters for GET /api/v1/repositories/{id}/imports."""

    import_type: ImportType | None = Field(
        None,
        description="Filter by import type (import, from_import, require, …).",
    )
    file_id: UUID | None = Field(
        None,
        description="Return only imports belonging to this file.",
    )
    target_module_contains: str | None = Field(
        None,
        description="Case-insensitive substring match on the target module.",
    )
    source_symbol_contains: str | None = Field(
        None,
        description="Case-insensitive substring match on the imported symbol name.",
    )
    page: int = Field(1, ge=1, description="Page number (1-indexed).")
    page_size: int = Field(50, ge=1, le=200, description="Items per page.")
