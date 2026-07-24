"""Repository import & management endpoints.

Routes
------
POST   /api/v1/repositories/import         Import and scan a local path
GET    /api/v1/repositories                List all repositories
GET    /api/v1/repositories/{id}           Get single repo + live stats
GET    /api/v1/repositories/{id}/files     Paginated file list
DELETE /api/v1/repositories/{id}           Delete repo and all files
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.database import get_db
from forgeai.schemas.repository import (
    FilesListResponse,
    FileResponse,
    ImportRequest,
    ImportResponse,
    RepositoryListItem,
    RepositoryResponse,
    RepositoryStats,
)
from forgeai.services.repository_service import RepositoryService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/repositories", tags=["Repositories"])


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_service(db: AsyncSession = Depends(get_db)) -> RepositoryService:
    return RepositoryService(db)


# ── POST /import ──────────────────────────────────────────────────────────────

@router.post(
    "/import",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import a local repository",
    description=(
        "Accept an absolute local path, scan its files, detect languages, "
        "and persist metadata to the database. Returns scan statistics."
    ),
)
async def import_repository(
    body: ImportRequest,
    svc: RepositoryService = Depends(_get_service),
) -> ImportResponse:
    """Import and scan a local directory."""
    try:
        return await svc.import_repository(body.path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("import_repository_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository scan failed. Check server logs for details.",
        ) from exc


# ── GET / ─────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[RepositoryListItem],
    summary="List all repositories",
)
async def list_repositories(
    svc: RepositoryService = Depends(_get_service),
) -> list[RepositoryListItem]:
    """Return all imported repositories with their latest scan stats."""
    repos = await svc.list_repositories()
    items: list[RepositoryListItem] = []

    for repo in repos:
        stats: RepositoryStats | None = None
        if repo.status.value == "ready":
            stats = await svc.get_stats(repo.id)

        items.append(
            RepositoryListItem(
                id=repo.id,
                name=repo.name,
                root_path=repo.root_path,
                status=repo.status.value,
                scan_version=repo.scan_version,
                last_scanned=repo.last_scanned,
                stats=stats,
            )
        )

    return items


# ── GET /{id} ─────────────────────────────────────────────────────────────────

@router.get(
    "/{repo_id}",
    response_model=RepositoryResponse,
    summary="Get a single repository",
)
async def get_repository(
    repo_id: uuid.UUID,
    svc: RepositoryService = Depends(_get_service),
) -> RepositoryResponse:
    """Fetch full repository record including live scan statistics."""
    repo = await svc.get_repository(repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )

    stats: RepositoryStats | None = None
    if repo.status.value == "ready":
        stats = await svc.get_stats(repo_id)

    return RepositoryResponse(
        id=repo.id,
        name=repo.name,
        root_path=repo.root_path,
        status=repo.status.value,
        scan_version=repo.scan_version,
        default_branch=repo.default_branch,
        current_commit=repo.current_commit,
        git_remote=repo.git_remote,
        created_at=repo.created_at,
        last_scanned=repo.last_scanned,
        stats=stats,
    )


# ── GET /{id}/files ───────────────────────────────────────────────────────────

@router.get(
    "/{repo_id}/files",
    response_model=FilesListResponse,
    summary="List files in a repository",
)
async def list_files(
    repo_id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    svc: RepositoryService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
) -> FilesListResponse:
    """Return a paginated list of files for the given repository."""
    repo = await svc.get_repository(repo_id)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )

    from forgeai.repositories.file_repo import FileRepo

    file_repo = FileRepo(db)
    files, total = await file_repo.list_by_repo(
        repo_id, page=page, page_size=page_size
    )

    return FilesListResponse(
        items=[
            FileResponse(
                id=f.id,
                repository_id=f.repository_id,
                relative_path=f.relative_path,
                language=f.language,
                extension=f.extension,
                size=f.size,
                is_binary=f.is_binary,
                mime_type=f.mime_type,
                line_count=f.line_count,
                last_modified=f.last_modified,
                parsed=f.parsed,
                symbols_count=f.symbols_count,
            )
            for f in files
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── DELETE /{id} ──────────────────────────────────────────────────────────────

@router.delete(
    "/{repo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a repository",
    description="Permanently delete a repository and all its scanned files.",
)
async def delete_repository(
    repo_id: uuid.UUID,
    svc: RepositoryService = Depends(_get_service),
) -> None:
    """Delete a repository and cascade-delete all its files."""
    deleted = await svc.delete_repository(repo_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )
