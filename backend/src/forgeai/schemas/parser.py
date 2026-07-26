"""Pydantic DTOs for the parser API.

Request/response schemas for parse-triggering endpoints:
  - ParseRequest: optional configuration for a parse run
  - ParseStatsResponse: per-language breakdown of parse results
  - ParseResponse: top-level result after parsing a repository

Phase 3 — Tree-sitter Code Parsing & Code Intelligence
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────────

class ParseRequest(BaseModel):
    """Optional body for POST /api/v1/repositories/{id}/parse.

    All fields are optional — calling with an empty body parses every
    eligible file in the repository.
    """

    force: bool = Field(
        False,
        description=(
            "When True, re-parse all files even if they have already been "
            "parsed in this scan version."
        ),
    )
    file_ids: list[UUID] | None = Field(
        None,
        description=(
            "If provided, parse only these specific files instead of the "
            "full repository."
        ),
    )
    languages: list[str] | None = Field(
        None,
        description=(
            "If provided, limit parsing to files of these languages "
            "(e.g. ['Python', 'TypeScript'])."
        ),
    )


# ── Stats ─────────────────────────────────────────────────────────────────────

class LanguageParseStats(BaseModel):
    """Parse statistics for a single language."""

    language: str
    files_parsed: int = 0
    symbols_extracted: int = 0
    imports_extracted: int = 0
    errors: int = 0


class ParseStatsResponse(BaseModel):
    """Aggregate parse statistics returned after a parse run."""

    total_files_parsed: int = 0
    total_files_skipped: int = Field(
        0, description="Files skipped (unsupported language or binary)."
    )
    total_files_failed: int = 0
    total_symbols: int = 0
    total_imports: int = 0
    by_language: list[LanguageParseStats] = Field(default_factory=list)

    # Breakdown by symbol type
    functions: int = 0
    classes: int = 0
    methods: int = 0
    interfaces: int = 0
    variables: int = 0
    other_symbols: int = 0


# ── Parse response ────────────────────────────────────────────────────────────

class ParseResponse(BaseModel):
    """Returned after POST /api/v1/repositories/{id}/parse completes."""

    repository_id: UUID
    status: str = Field(description="Repository status after parsing.")
    parse_time_ms: int = Field(
        ..., description="Wall-clock time of the parse in milliseconds."
    )
    stats: ParseStatsResponse
