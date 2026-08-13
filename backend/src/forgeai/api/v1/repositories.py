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
from forgeai.repositories.import_repo import ImportRepo
from forgeai.repositories.symbol_repo import SymbolRepo
from forgeai.schemas.embedding import (
    IndexRequest,
    IndexResponse,
    IndexStatsResponse,
)
from forgeai.schemas.import_ import ImportListResponse, ImportRecordResponse
from forgeai.schemas.parser import ParseRequest, ParseResponse
from forgeai.schemas.repository import (
    FileResponse,
    FilesListResponse,
    ImportRequest,
    ImportResponse,
    RepositoryListItem,
    RepositoryResponse,
    RepositoryStats,
)
from forgeai.schemas.search import (
    SearchQueryRequest,
    SearchResponse,
    SearchType,
)
from forgeai.schemas.symbol import SymbolListResponse, SymbolResponse
from forgeai.services.knowledge_base import KnowledgeBaseService
from forgeai.services.parser import CodeParserService
from forgeai.services.repository_service import RepositoryService
from forgeai.services.search import SearchService

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
    files, total = await file_repo.list_by_repo(repo_id, page=page, page_size=page_size)

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


# ── POST /{id}/parse ──────────────────────────────────────────────────────────


@router.post(
    "/{repo_id}/parse",
    response_model=ParseResponse,
    summary="Parse source files in a repository",
    description="Extract symbols and imports from repository files using Tree-sitter AST parsing.",
)
async def parse_repository(
    repo_id: uuid.UUID,
    body: ParseRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> ParseResponse:
    """Parse source files in a repository using Tree-sitter."""
    parser_svc = CodeParserService(db)
    try:
        return await parser_svc.parse_repository(repo_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("parse_repository_failed", repo_id=str(repo_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository parsing failed. Check server logs for details.",
        ) from exc


# ── GET /{id}/symbols ─────────────────────────────────────────────────────────


@router.get(
    "/{repo_id}/symbols",
    response_model=SymbolListResponse,
    summary="List code symbols in a repository",
)
async def list_symbols(
    repo_id: uuid.UUID,
    file_id: uuid.UUID | None = Query(default=None, description="Filter by file UUID"),
    symbol_type: str | None = Query(
        default=None, description="Filter by symbol type (e.g. function, class)"
    ),
    name_query: str | None = Query(
        default=None, description="Case-insensitive name search"
    ),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> SymbolListResponse:
    """Return a paginated list of extracted code symbols."""
    symbol_repo = SymbolRepo(db)
    symbols, total = await symbol_repo.list_by_repo(
        repo_id,
        file_id=file_id,
        symbol_type=symbol_type,
        name_query=name_query,
        page=page,
        page_size=page_size,
    )

    return SymbolListResponse(
        items=[
            SymbolResponse(
                id=s.id,
                repository_id=s.repository_id,
                file_id=s.file_id,
                name=s.name,
                symbol_type=s.symbol_type.value,
                language=s.language,
                parent_symbol_id=s.parent_symbol_id,
                start_line=s.start_line,
                end_line=s.end_line,
                start_column=s.start_column,
                end_column=s.end_column,
                visibility=s.visibility.value if s.visibility else None,
                signature=s.signature,
                docstring=s.docstring,
            )
            for s in symbols
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /{id}/imports ─────────────────────────────────────────────────────────


@router.get(
    "/{repo_id}/imports",
    response_model=ImportListResponse,
    summary="List import dependencies in a repository",
)
async def list_imports(
    repo_id: uuid.UUID,
    file_id: uuid.UUID | None = Query(default=None, description="Filter by file UUID"),
    import_type: str | None = Query(
        default=None, description="Filter by import type (e.g. import, from_import)"
    ),
    module_query: str | None = Query(
        default=None, description="Case-insensitive module search"
    ),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> ImportListResponse:
    """Return a paginated list of extracted import dependencies."""
    import_repo = ImportRepo(db)
    imports, total = await import_repo.list_by_repo(
        repo_id,
        file_id=file_id,
        import_type=import_type,
        module_query=module_query,
        page=page,
        page_size=page_size,
    )

    return ImportListResponse(
        items=[
            ImportRecordResponse(
                id=imp.id,
                repository_id=imp.repository_id,
                file_id=imp.file_id,
                source_symbol=imp.source_symbol,
                target_module=imp.target_module,
                import_type=imp.import_type.value,
                alias=imp.alias,
            )
            for imp in imports
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── POST /{id}/index ─────────────────────────────────────────────────────────


@router.post(
    "/{repo_id}/index",
    response_model=IndexResponse,
    summary="Index repository into vector embeddings",
    description="Chunk repository files and generate 1536-dim vector embeddings.",
)
async def index_repository(
    repo_id: uuid.UUID,
    body: IndexRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> IndexResponse:
    """Index repository files into vector embeddings."""
    kb_svc = KnowledgeBaseService(db)
    try:
        return await kb_svc.index_repository(repo_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("index_repository_failed", repo_id=str(repo_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Repository indexing failed. Check server logs for details.",
        ) from exc


# ── GET /{id}/index/stats ───────────────────────────────────────────────────


@router.get(
    "/{repo_id}/index/stats",
    response_model=IndexStatsResponse,
    summary="Get repository vector index stats",
)
async def get_index_stats(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IndexStatsResponse:
    """Fetch vector index statistics for a repository."""
    kb_svc = KnowledgeBaseService(db)
    try:
        return await kb_svc.get_index_stats(repo_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ── DELETE /{id}/index ───────────────────────────────────────────────────────


@router.delete(
    "/{repo_id}/index",
    status_code=status.HTTP_200_OK,
    summary="Clear repository vector index",
)
async def clear_index(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Delete all vector embeddings for a repository."""
    kb_svc = KnowledgeBaseService(db)
    deleted = await kb_svc.clear_index(repo_id)
    return {"deleted": deleted}


# ── POST /{id}/search ────────────────────────────────────────────────────────


@router.post(
    "/{repo_id}/search",
    response_model=SearchResponse,
    summary="Multi-modal repository code search",
    description="Perform semantic, keyword, symbol, or RRF hybrid search over repository code.",
)
async def search_repository(
    repo_id: uuid.UUID,
    body: SearchQueryRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Multi-modal search (hybrid RRF, semantic, keyword, symbol)."""
    search_svc = SearchService(db)
    try:
        return await search_svc.search(repo_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("search_repository_failed", repo_id=str(repo_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code search failed. Check server logs for details.",
        ) from exc


# ── GET /{id}/search ─────────────────────────────────────────────────────────


@router.get(
    "/{repo_id}/search",
    response_model=SearchResponse,
    summary="Multi-modal search (GET query params)",
)
async def search_repository_get(
    repo_id: uuid.UUID,
    q: str = Query(..., min_length=1, description="Search query string"),
    type: str = Query(default="hybrid", description="Search type: hybrid, semantic, keyword, symbol"),
    limit: int = Query(default=10, ge=1, le=100, description="Max results"),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0, description="Min score filter"),
    language: str | None = Query(default=None, description="Language filter"),
    extension: str | None = Query(default=None, description="Extension filter"),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """GET query-params endpoint for multi-modal code search."""
    search_svc = SearchService(db)
    try:
        search_type_enum = SearchType(type.lower())
    except ValueError:
        search_type_enum = SearchType.hybrid

    req = SearchQueryRequest(
        query=q,
        search_type=search_type_enum,
        limit=limit,
        min_score=min_score,
        language=language,
        extension=extension,
    )
    try:
        return await search_svc.search(repo_id, req)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

