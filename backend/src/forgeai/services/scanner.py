"""Repository file scanner service.

Recursively walks a local directory, collects file metadata,
detects programming languages, and computes statistics.

Usage
-----
    scanner = RepositoryScanner(root_path=Path("/my/project"))
    result = scanner.scan()
    # result.files  → list[ScannedFile]
    # result.stats  → ScanStats
"""

from __future__ import annotations

import hashlib
import mimetypes
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import structlog

logger = structlog.get_logger(__name__)

# ── Language map ──────────────────────────────────────────────────────────────
#   Extension → human-readable language name.
#   Add new entries here; no code changes needed elsewhere.
LANGUAGE_MAP: Final[dict[str, str]] = {
    # Python
    ".py": "Python",
    ".pyi": "Python",
    ".pyx": "Python",
    # JavaScript / TypeScript
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mts": "TypeScript",
    # Web
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SCSS",
    ".less": "LESS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    # Systems
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hxx": "C++",
    ".rs": "Rust",
    ".go": "Go",
    ".zig": "Zig",
    # JVM
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".groovy": "Groovy",
    ".scala": "Scala",
    # Mobile
    ".swift": "Swift",
    ".m": "Objective-C",
    ".mm": "Objective-C",
    ".dart": "Dart",
    # Scripting
    ".rb": "Ruby",
    ".php": "PHP",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".fish": "Shell",
    ".ps1": "PowerShell",
    # Functional
    ".hs": "Haskell",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".clj": "Clojure",
    ".ml": "OCaml",
    ".fs": "F#",
    ".fsx": "F#",
    # Data / Config
    ".json": "JSON",
    ".jsonc": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".ini": "INI",
    ".env": "ENV",
    ".xml": "XML",
    ".csv": "CSV",
    # Infra / DevOps
    ".tf": "Terraform",
    ".hcl": "HCL",
    ".dockerfile": "Dockerfile",
    ".proto": "Protobuf",
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    # Docs / Markup
    ".md": "Markdown",
    ".mdx": "Markdown",
    ".rst": "reStructuredText",
    ".tex": "LaTeX",
    ".txt": "Text",
    # Query
    ".sql": "SQL",
    # R / Julia / Notebooks
    ".r": "R",
    ".jl": "Julia",
}

# Extensions whose files are always considered "code" for statistics
CODE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".py",
        ".pyi",
        ".pyx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".mts",
        ".vue",
        ".svelte",
        ".c",
        ".h",
        ".cpp",
        ".cc",
        ".cxx",
        ".hpp",
        ".hxx",
        ".rs",
        ".go",
        ".zig",
        ".java",
        ".kt",
        ".kts",
        ".groovy",
        ".scala",
        ".swift",
        ".m",
        ".mm",
        ".dart",
        ".rb",
        ".php",
        ".lua",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".hs",
        ".ex",
        ".exs",
        ".erl",
        ".clj",
        ".ml",
        ".fs",
        ".fsx",
        ".sql",
        ".r",
        ".jl",
        ".tf",
        ".hcl",
        ".proto",
        ".graphql",
        ".gql",
    }
)

# Directories to skip during traversal.
# Later phases can merge this with project-specific .gitignore entries.
DEFAULT_IGNORE: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".next",
        ".nuxt",
        ".turbo",
        "dist",
        "build",
        "out",
        ".venv",
        "venv",
        "env",
        ".tox",
        "coverage",
        ".coverage",
        ".cache",
        ".idea",
        ".vscode",
        "tmp",
        "temp",
        "logs",
        ".DS_Store",
    }
)

# Max bytes read when checking for binary content
_BINARY_PROBE_BYTES: Final[int] = 8192


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ScannedFile:
    """Metadata for a single file discovered during a scan."""

    id: uuid.UUID
    relative_path: str
    absolute_path: str
    language: str | None
    extension: str
    size: int
    sha256: str | None
    last_modified: datetime | None
    is_binary: bool
    mime_type: str | None
    line_count: int


@dataclass(slots=True)
class ScanStats:
    """Aggregate statistics computed after a completed scan."""

    total_files: int
    code_files: int
    total_size_bytes: int
    languages: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ScanResult:
    """Full output of a repository scan."""

    files: list[ScannedFile]
    stats: ScanStats
    git_info: dict[str, str | None]
    scan_time_ms: int


# ── Scanner ───────────────────────────────────────────────────────────────────


class RepositoryScanner:
    """Recursively scans a local repository and collects file metadata.

    Parameters
    ----------
    root_path:
        Absolute path to the repository root directory.
    extra_ignore:
        Additional directory or file names to skip (merged with DEFAULT_IGNORE).
    max_file_size_bytes:
        Files larger than this are recorded but content is not hashed/counted.
        Defaults to 5 MB.
    """

    def __init__(
        self,
        root_path: Path,
        extra_ignore: frozenset[str] | None = None,
        max_file_size_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self.root = root_path.resolve()
        self.ignore = DEFAULT_IGNORE | (extra_ignore or frozenset())
        self.max_file_size_bytes = max_file_size_bytes

    # ── Public API ────────────────────────────────────────────────────────────

    def scan(self) -> ScanResult:
        """Run the scan and return a ScanResult.

        This is intentionally synchronous — the FastAPI endpoint runs it
        in a thread pool executor so it does not block the event loop.
        """
        import time

        log = logger.bind(root=str(self.root))
        log.info("scanner_started")
        t0 = time.monotonic()

        files = list(self._walk())
        stats = self._compute_stats(files)
        git_info = self._detect_git_info()

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        log.info(
            "scanner_finished",
            total_files=stats.total_files,
            code_files=stats.code_files,
            elapsed_ms=elapsed_ms,
        )

        return ScanResult(
            files=files,
            stats=stats,
            git_info=git_info,
            scan_time_ms=elapsed_ms,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _walk(self) -> list[ScannedFile]:
        scanned: list[ScannedFile] = []

        for entry in self._iter_files(self.root):
            try:
                stat = entry.stat()
            except OSError:
                continue  # Permission denied or broken symlink

            ext = entry.suffix.lower()
            abs_path = str(entry)
            rel_path = str(entry.relative_to(self.root))

            is_binary = self._is_binary(entry, stat.st_size)
            mime_type = self._guess_mime(entry)
            sha256, line_count = self._content_metrics(entry, stat.st_size, is_binary)

            last_modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)

            scanned.append(
                ScannedFile(
                    id=uuid.uuid4(),
                    relative_path=rel_path,
                    absolute_path=abs_path,
                    language=LANGUAGE_MAP.get(ext),
                    extension=ext,
                    size=stat.st_size,
                    sha256=sha256,
                    last_modified=last_modified,
                    is_binary=is_binary,
                    mime_type=mime_type,
                    line_count=line_count,
                )
            )

        return scanned

    def _iter_files(self, directory: Path):  # type: ignore[return]
        """Yield file paths, skipping ignored directories."""
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if entry.name in self.ignore:
                continue
            if entry.is_symlink():
                continue
            if entry.is_dir():
                yield from self._iter_files(entry)
            elif entry.is_file():
                yield entry

    def _is_binary(self, path: Path, size: int) -> bool:
        """Return True if the file appears to be binary.

        Uses the same heuristic as ``git diff``: read the first 8 KiB
        and check for a null byte.
        """
        if size == 0:
            return False
        try:
            with path.open("rb") as fh:
                chunk = fh.read(_BINARY_PROBE_BYTES)
            return b"\x00" in chunk
        except OSError:
            return False

    def _guess_mime(self, path: Path) -> str | None:
        mime, _ = mimetypes.guess_type(str(path))
        return mime

    def _content_metrics(
        self, path: Path, size: int, is_binary: bool
    ) -> tuple[str | None, int]:
        """Return (sha256_hex, line_count).

        Skips hashing & line counting for binary or oversized files.
        """
        if is_binary or size > self.max_file_size_bytes:
            return None, 0

        try:
            raw = path.read_bytes()
        except OSError:
            return None, 0

        sha = hashlib.sha256(raw).hexdigest()
        try:
            line_count = raw.decode("utf-8", errors="replace").count("\n")
        except Exception:
            line_count = 0

        return sha, line_count

    def _compute_stats(self, files: list[ScannedFile]) -> ScanStats:
        languages: dict[str, int] = {}
        code_files = 0
        total_size = 0

        for f in files:
            total_size += f.size
            if f.extension in CODE_EXTENSIONS:
                code_files += 1
            if f.language:
                languages[f.language] = languages.get(f.language, 0) + 1

        # Sort by count descending for nicer display
        sorted_langs = dict(
            sorted(languages.items(), key=lambda kv: kv[1], reverse=True)
        )

        return ScanStats(
            total_files=len(files),
            code_files=code_files,
            total_size_bytes=total_size,
            languages=sorted_langs,
        )

    def _detect_git_info(self) -> dict[str, str | None]:
        """Try to read Git metadata from the repository root.

        Falls back to ``None`` values when the directory is not a git repo
        or git is not installed.
        """
        info: dict[str, str | None] = {
            "default_branch": None,
            "current_commit": None,
            "git_remote": None,
        }

        if not (self.root / ".git").exists():
            return info

        def _run(args: list[str]) -> str | None:
            try:
                result = subprocess.run(
                    args,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.stdout.strip() if result.returncode == 0 else None
            except Exception:
                return None

        info["default_branch"] = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        info["current_commit"] = _run(["git", "rev-parse", "HEAD"])
        info["git_remote"] = _run(["git", "remote", "get-url", "origin"])

        return info
