"""Repository chat Pydantic DTO schemas.

Phase 6 — Repository Chat & Grounded QA
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from forgeai.models.chat import MessageRole


class CitationItem(BaseModel):
    """Grounded source citation reference pointing to a file and line range."""

    model_config = ConfigDict(from_attributes=True)

    file_id: UUID
    relative_path: str
    symbol_id: UUID | None = None
    name: str | None = None
    start_line: int = 1
    end_line: int = 1
    score: float = Field(
        default=0.0,
        ge=0.0,
        description="Relevance or similarity score.",
    )


class ChatSessionCreate(BaseModel):
    """Payload to create a new chat session for a repository."""

    title: str = Field(
        default="New Conversation",
        max_length=255,
        description="Title or topic of the chat session.",
    )


class ChatSessionResponse(BaseModel):
    """API response DTO representing a chat session."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatSessionListResponse(BaseModel):
    """Paginated list response wrapper for chat sessions."""

    items: list[ChatSessionResponse]
    total: int


class ChatMessageCreate(BaseModel):
    """Payload to send a new user prompt in a chat session."""

    content: str = Field(
        min_length=1,
        description="User question or prompt for the repository code.",
    )
    search_type: str = Field(
        default="hybrid",
        description="Search modality for grounding ('hybrid', 'semantic', 'keyword', 'symbol').",
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Minimum score threshold for context inclusion.",
    )


class ChatMessageResponse(BaseModel):
    """API response DTO representing a chat message with grounded citations."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    citations: list[CitationItem] = Field(default_factory=list)
    token_count: int = 0
    created_at: datetime


class ChatStreamChunk(BaseModel):
    """Server-Sent Event (SSE) chunk payload for live streaming AI answers."""

    event: str = Field(
        description="Event type ('token', 'citation', 'done', 'error').",
    )
    data: str = Field(
        description="Event content data.",
    )
