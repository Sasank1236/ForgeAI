"""Auto documentation API endpoints.

Routes
------
POST   /api/v1/repositories/{repo_id}/docs/generate   Generate technical documentation
GET    /api/v1/repositories/{repo_id}/docs            List generated documentation
GET    /api/v1/docs/{doc_id}                           Get documentation details
PUT    /api/v1/docs/{doc_id}                           Update documentation content
DELETE /api/v1/docs/{doc_id}                           Delete documentation

Phase 8 — Auto Documentation Generation
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.database import get_db
from forgeai.schemas.documentation import (
    DocGenerateRequest,
    DocUpdateRequest,
    DocumentationListResponse,
    DocumentationResponse,
)
from forgeai.services.documentation_service import DocumentationService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Auto Documentation"])


@router.post(
    "/repositories/{repo_id}/docs/generate",
    response_model=DocumentationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate repository technical documentation",
)
async def generate_repository_docs(
    repo_id: uuid.UUID,
    body: DocGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentationResponse:
    """Analyze repository AST & structure to generate README, Architecture, or API Reference docs."""
    doc_svc = DocumentationService(db)
    try:
        return await doc_svc.generate_documentation(repo_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/repositories/{repo_id}/docs",
    response_model=DocumentationListResponse,
    summary="List documentation records for a repository",
)
async def list_repository_docs(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentationListResponse:
    """Fetch all generated documentation records for a repository."""
    doc_svc = DocumentationService(db)
    return await doc_svc.list_documentation(repo_id)


@router.get(
    "/docs/{doc_id}",
    response_model=DocumentationResponse,
    summary="Get documentation details",
)
async def get_documentation(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentationResponse:
    """Fetch a single documentation record by UUID."""
    doc_svc = DocumentationService(db)
    try:
        return await doc_svc.get_documentation(doc_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put(
    "/docs/{doc_id}",
    response_model=DocumentationResponse,
    summary="Update documentation content",
)
async def update_documentation(
    doc_id: uuid.UUID,
    body: DocUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentationResponse:
    """Update documentation Markdown content or title."""
    doc_svc = DocumentationService(db)
    try:
        return await doc_svc.update_documentation(doc_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/docs/{doc_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a documentation record",
)
async def delete_documentation(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Delete a documentation record."""
    doc_svc = DocumentationService(db)
    success = await doc_svc.delete_documentation(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documentation {doc_id} not found.",
        )
    return {"deleted": True}
