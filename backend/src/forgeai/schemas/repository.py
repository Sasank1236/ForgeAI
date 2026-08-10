"""Pydantic DTOs for the repository import & file scanner API.

All schemas use snake_case field names (FastAPI serialises to camelCase
on the way out only if configured; we keep snake_case for consistency).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Request ───────────────────────────────────────────────────────────────────


class ImportRequest(BaseModel):
    """Body for POST /api/v1/repositories/import."""

    path: str = Field(
        ...,
        description="Absolute path to a local repository root directory.",
        examples=["C:/Users/dev/my-project", "/home/dev/my-project"],
    )


# ── Stats ─────────────────────────────────────────────────────────────────────


class RepositoryStats(BaseModel):
    """Aggregate statistics computed after a repository scan."""

    total_files: int = Field(..., description="Total files discovered.")
    code_files: int = Field(..., description="Files with a recognised code extension.")
    total_size_bytes: int = Field(
        ..., description="Combined size of all files in bytes."
    )
    languages: dict[str, int] = Field(
        default_factory=dict,
        description="Map of language name → file count, sorted by count descending.",
    )


# ── Import response ───────────────────────────────────────────────────────────


class ImportResponse(BaseModel):
    """Returned after POST /api/v1/repositories/import completes."""

    repository_id: UUID
    status: str = Field(description="Repository status after the import.")
    files_scanned: int
    languages: dict[str, int]
    scan_time_ms: int = Field(
        description="Wall-clock time of the scan in milliseconds."
    )


# ── Repository representations ────────────────────────────────────────────────


class RepositoryResponse(BaseModel):
    """Full repository record including scan statistics."""

    id: UUID
    name: str
    root_path: str
    status: str
    scan_version: int
    # Git info
    default_branch: str | None = None
    current_commit: str | None = None
    git_remote: str | None = None
    # Timestamps
    created_at: datetime
    last_scanned: datetime | None = None
    # Nested stats (None when status is pending/scanning)
    stats: RepositoryStats | None = None

    model_config = {"from_attributes": True}


class RepositoryListItem(BaseModel):
    """Slim card representation used in GET /api/v1/repositories."""

    id: UUID
    name: str
    root_path: str
    status: str
    scan_version: int
    last_scanned: datetime | None = None
    stats: RepositoryStats | None = None

    model_config = {"from_attributes": True}


# ── File representations ──────────────────────────────────────────────────────


class FileResponse(BaseModel):
    """Single file record returned by GET /api/v1/repositories/{id}/files."""

    id: UUID
    repository_id: UUID
    relative_path: str
    language: str | None = None
    extension: str
    size: int
    is_binary: bool
    mime_type: str | None = None
    line_count: int
    last_modified: datetime | None = None
    # Phase 3 fields (already in schema, populated later)
    parsed: bool
    symbols_count: int

    model_config = {"from_attributes": True}


class FilesListResponse(BaseModel):
    """Paginated list of files for a repository."""

    items: list[FileResponse]
    total: int
    page: int
    page_size: int
