"""Auto documentation Pydantic DTO schemas.

Phase 8 — Auto Documentation Generation
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from forgeai.models.documentation import DocStatus, DocType


class DocGenerateRequest(BaseModel):
    """Payload to trigger auto documentation generation for a repository."""

    doc_type: DocType = Field(
        default=DocType.readme,
        description="Type of documentation to generate ('readme', 'architecture', 'api_reference', 'symbol_doc').",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Custom title for the generated document.",
    )
    custom_instructions: str | None = Field(
        default=None,
        description="Additional context or formatting instructions for generation.",
    )


class DocUpdateRequest(BaseModel):
    """Payload to update documentation content."""

    content: str = Field(
        min_length=1,
        description="Updated Markdown content for the document.",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Updated document title.",
    )


class DocumentationResponse(BaseModel):
    """API response DTO representing generated repository technical documentation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    doc_type: DocType
    title: str
    content: str
    file_path: str | None = None
    status: DocStatus
    created_at: datetime
    updated_at: datetime


class DocumentationListResponse(BaseModel):
    """Paginated list response wrapper for technical documentation."""

    items: list[DocumentationResponse]
    total: int
