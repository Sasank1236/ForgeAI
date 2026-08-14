"""Repository chat & streaming API endpoints.

Routes
------
POST   /api/v1/repositories/{repo_id}/chat/sessions   Create a chat session
GET    /api/v1/repositories/{repo_id}/chat/sessions   List chat sessions
GET    /api/v1/chat/sessions/{session_id}              Get session details + message history
DELETE /api/v1/chat/sessions/{session_id}              Delete chat session
POST   /api/v1/chat/sessions/{session_id}/messages    Send user message
POST   /api/v1/chat/sessions/{session_id}/stream      Stream response tokens (SSE)

Phase 6 — Repository Chat & Grounded QA
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.database import get_db
from forgeai.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from forgeai.services.chat_service import ChatService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Repository Chat"])


# ── Sessions Endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/repositories/{repo_id}/chat/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a chat session",
)
async def create_chat_session(
    repo_id: uuid.UUID,
    body: ChatSessionCreate | None = None,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """Create a new codebase chat session."""
    chat_svc = ChatService(db)
    try:
        return await chat_svc.create_session(repo_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/repositories/{repo_id}/chat/sessions",
    response_model=ChatSessionListResponse,
    summary="List chat sessions for a repository",
)
async def list_chat_sessions(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionListResponse:
    """List all chat sessions for a repository."""
    chat_svc = ChatService(db)
    return await chat_svc.list_sessions(repo_id)


@router.get(
    "/chat/sessions/{session_id}",
    summary="Get chat session details + message history",
)
async def get_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch session details and full message history."""
    chat_svc = ChatService(db)
    try:
        sess, messages = await chat_svc.get_session(session_id)
        return {
            "session": sess,
            "messages": messages,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/chat/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a chat session",
)
async def delete_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Delete a chat session and its history."""
    chat_svc = ChatService(db)
    success = await chat_svc.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found.",
        )
    return {"deleted": True}


# ── Messages & Streaming Endpoints ─────────────────────────────────────────────


@router.post(
    "/chat/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    summary="Send a chat message",
)
async def send_chat_message(
    session_id: uuid.UUID,
    body: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """Send user prompt and return assistant response with grounded citations."""
    chat_svc = ChatService(db)
    try:
        return await chat_svc.send_message(session_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/chat/sessions/{session_id}/stream",
    summary="Stream assistant answer via SSE (Server-Sent Events)",
)
async def stream_chat_message(
    session_id: uuid.UUID,
    body: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream AI answer tokens live via Server-Sent Events."""
    chat_svc = ChatService(db)
    generator = chat_svc.stream_message(session_id, body)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
