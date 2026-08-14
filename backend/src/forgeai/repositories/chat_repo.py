"""Chat data-access layer.

Thin async SQLAlchemy queries for the chat_sessions and chat_messages tables.

Phase 6 — Repository Chat & Grounded QA
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from forgeai.models.chat import ChatMessage, ChatSession, MessageRole

logger = structlog.get_logger(__name__)


class ChatRepo:
    """CRUD operations for the ``chat_sessions`` and ``chat_messages`` tables."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_session(
        self,
        repository_id: UUID,
        title: str = "New Conversation",
    ) -> ChatSession:
        """Create a new chat session for a repository."""
        session = ChatSession(
            repository_id=repository_id,
            title=title,
        )
        self._db.add(session)
        await self._db.flush()
        logger.info(
            "chat_session_created",
            session_id=str(session.id),
            repo_id=str(repository_id),
            title=title,
        )
        return session

    async def get_session(self, session_id: UUID) -> ChatSession | None:
        """Fetch a single chat session by UUID with messages preloaded."""
        stmt = (
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions_by_repo(
        self,
        repository_id: UUID,
    ) -> list[tuple[ChatSession, int]]:
        """Return list of sessions for a repository with message counts."""
        stmt = (
            select(
                ChatSession,
                func.count(ChatMessage.id).label("message_count"),
            )
            .outerjoin(ChatMessage, ChatSession.id == ChatMessage.session_id)
            .where(ChatSession.repository_id == repository_id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.updated_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.all())

    async def delete_session(self, session_id: UUID) -> int:
        """Delete a chat session and all associated messages."""
        stmt = delete(ChatSession).where(ChatSession.id == session_id)
        result = await self._db.execute(stmt)
        return result.rowcount

    async def add_message(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        citations: list[dict] | None = None,
        token_count: int = 0,
    ) -> ChatMessage:
        """Append a message to a chat session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations or [],
            token_count=token_count,
        )
        self._db.add(message)
        await self._db.flush()

        # Touch session updated_at timestamp
        session = await self._db.get(ChatSession, session_id)
        if session:
            session.updated_at = message.created_at

        return message

    async def list_messages(self, session_id: UUID) -> list[ChatMessage]:
        """Fetch all messages for a chat session ordered chronologically."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
