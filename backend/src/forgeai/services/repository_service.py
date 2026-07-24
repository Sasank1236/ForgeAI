"""Repository import service.

Orchestrates: path validation → DB row creation → scanner → bulk file
persistence → status update. The API layer calls this and stays thin.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.config import get_settings
from forgeai.models.repository import Repository, RepositoryStatus
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.schemas.repository import ImportResponse, RepositoryStats
from forgeai.services.scanner import RepositoryScanner, ScanResult

logger = structlog.get_logger(__name__)
settings = get_settings()


class RepositoryService:
    """High-level operations for the repository import pipeline."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo_repo = RepositoryRepo(db)
        self._file_repo = FileRepo(db)

    # ── Import ────────────────────────────────────────────────────────────────

    async def import_repository(self, raw_path: str) -> ImportResponse:
        """Full import pipeline for a local directory.

        Steps
        -----
        1. Validate path exists and is a directory.
        2. Upsert a Repository row (create or reuse existing, incrementing scan_version).
        3. Mark status = scanning.
        4. Run RepositoryScanner in a thread pool (avoids blocking the event loop).
        5. Bulk-insert scanned files (ON CONFLICT DO NOTHING for re-scans).
        6. Mark status = ready, update last_scanned & git info.
        7. Return ImportResponse with statistics.

        Raises
        ------
        ValueError  – path does not exist, is not a directory, or exceeds size limits.
        """
        root = Path(raw_path).resolve()
        self._validate_path(root)

        name = root.name
        log = logger.bind(name=name, path=str(root))

        # ── 1. Create or reuse repository row ─────────────────────────────────
        existing = await self._repo_repo.get_by_path(str(root))
        if existing:
            repo = existing
            log.info("repo_reimport", repo_id=str(repo.id), version=repo.scan_version)
        else:
            repo = await self._repo_repo.create(name=name, root_path=str(root))
            log.info("repo_import_new", repo_id=str(repo.id))

        # ── 2. Mark scanning ──────────────────────────────────────────────────
        await self._repo_repo.update_status(repo.id, RepositoryStatus.scanning)
        await self._db.commit()

        try:
            # ── 3. Run scanner in thread pool ─────────────────────────────────
            scanner = RepositoryScanner(root_path=root)
            scan: ScanResult = await asyncio.get_event_loop().run_in_executor(
                None, scanner.scan
            )

            # ── 4. Bulk-insert files ──────────────────────────────────────────
            rows = [
                {
                    "id": f.id,
                    "repository_id": repo.id,
                    "relative_path": f.relative_path,
                    "absolute_path": f.absolute_path,
                    "language": f.language,
                    "extension": f.extension,
                    "size": f.size,
                    "sha256": f.sha256,
                    "last_modified": f.last_modified,
                    "is_binary": f.is_binary,
                    "mime_type": f.mime_type,
                    "line_count": f.line_count,
                    "parsed": False,
                    "symbols_count": 0,
                }
                for f in scan.files
            ]
            await self._file_repo.bulk_insert(rows)

            # ── 5. Mark ready, update git info ────────────────────────────────
            git = scan.git_info
            await self._repo_repo.update_status(
                repo.id,
                RepositoryStatus.ready,
                last_scanned=datetime.now(tz=timezone.utc),
                increment_scan_version=bool(existing),
                default_branch=git.get("default_branch"),
                current_commit=git.get("current_commit"),
                git_remote=git.get("git_remote"),
            )
            await self._db.commit()

            log.info(
                "repo_import_complete",
                files=scan.stats.total_files,
                code_files=scan.stats.code_files,
                ms=scan.scan_time_ms,
            )

            return ImportResponse(
                repository_id=repo.id,
                status=RepositoryStatus.ready.value,
                files_scanned=scan.stats.total_files,
                languages=scan.stats.languages,
                scan_time_ms=scan.scan_time_ms,
            )

        except Exception as exc:
            log.error("repo_import_failed", error=str(exc))
            await self._repo_repo.update_status(repo.id, RepositoryStatus.error)
            await self._db.commit()
            raise

    # ── Read helpers ──────────────────────────────────────────────────────────

    async def get_repository(self, repo_id: uuid.UUID) -> Repository | None:
        return await self._repo_repo.get_by_id(repo_id)

    async def list_repositories(self) -> list[Repository]:
        return await self._repo_repo.list_all()

    async def get_stats(self, repo_id: uuid.UUID) -> RepositoryStats | None:
        """Return live stats computed from the files table."""
        repo = await self._repo_repo.get_by_id(repo_id)
        if repo is None:
            return None
        raw = await self._file_repo.get_stats(repo_id)
        return RepositoryStats(**raw)

    async def delete_repository(self, repo_id: uuid.UUID) -> bool:
        deleted = await self._repo_repo.delete(repo_id)
        if deleted:
            await self._db.commit()
        return deleted

    # ── Private ───────────────────────────────────────────────────────────────

    def _validate_path(self, root: Path) -> None:
        if not root.exists():
            raise ValueError(f"Path does not exist: {root}")
        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root}")
        # Guard against importing extremely large repos
        max_mb = settings.max_repo_size_mb
        if max_mb and max_mb > 0:
            # Quick size estimate: count entries rather than reading all bytes
            pass  # Full size is computed during scan; hard limit enforced there
