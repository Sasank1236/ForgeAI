"""Auto documentation generator service.

Extracts AST symbols, file structures, and import dependency graphs to synthesize
production-ready Markdown documentation (README, Architecture, API Reference).

Phase 8 — Auto Documentation Generation
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from forgeai.config import get_settings
from forgeai.models.documentation import DocStatus, DocType
from forgeai.repositories.documentation_repo import DocumentationRepo
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.import_repo import ImportRepo
from forgeai.repositories.repository_repo import RepositoryRepo
from forgeai.repositories.symbol_repo import SymbolRepo
from forgeai.schemas.documentation import (
    DocGenerateRequest,
    DocUpdateRequest,
    DocumentationListResponse,
    DocumentationResponse,
)

logger = structlog.get_logger(__name__)


class DocumentationService:
    """Service orchestrating auto technical documentation synthesis."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._doc_repo = DocumentationRepo(db)
        self._repo_repo = RepositoryRepo(db)
        self._file_repo = FileRepo(db)
        self._symbol_repo = SymbolRepo(db)
        self._import_repo = ImportRepo(db)
        self._settings = get_settings()

    async def generate_documentation(
        self,
        repository_id: UUID,
        request: DocGenerateRequest,
    ) -> DocumentationResponse:
        """Analyze repository AST & file structure to generate technical documentation."""
        repo = await self._repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError(f"Repository {repository_id} not found.")

        # Gather repository metadata
        files = await self._file_repo.list_by_repository(repository_id)
        symbols = await self._symbol_repo.list_by_repository(repository_id)
        imports = await self._import_repo.list_by_repository(repository_id)

        # Synthesize Markdown based on doc_type
        doc_title, doc_content, default_file_path = await self._synthesize_doc(
            repo_name=repo.name,
            doc_type=request.doc_type,
            files=files,
            symbols=symbols,
            imports=imports,
            custom_title=request.title,
            custom_instructions=request.custom_instructions,
        )

        # Save or update in DB
        doc = await self._doc_repo.create_doc(
            repository_id=repository_id,
            doc_type=request.doc_type,
            title=doc_title,
            content=doc_content,
            file_path=default_file_path,
            status=DocStatus.generated,
        )
        await self._db.commit()

        logger.info(
            "documentation_generated",
            doc_id=str(doc.id),
            repo_id=str(repository_id),
            doc_type=request.doc_type,
        )

        return DocumentationResponse(
            id=doc.id,
            repository_id=doc.repository_id,
            doc_type=doc.doc_type,
            title=doc.title,
            content=doc.content,
            file_path=doc.file_path,
            status=doc.status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    async def list_documentation(self, repository_id: UUID) -> DocumentationListResponse:
        """List all generated documentation for a repository."""
        docs_orm = await self._doc_repo.list_docs_by_repo(repository_id)
        items = [
            DocumentationResponse(
                id=d.id,
                repository_id=d.repository_id,
                doc_type=d.doc_type,
                title=d.title,
                content=d.content,
                file_path=d.file_path,
                status=d.status,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs_orm
        ]
        return DocumentationListResponse(items=items, total=len(items))

    async def get_documentation(self, doc_id: UUID) -> DocumentationResponse:
        """Fetch documentation record by UUID."""
        doc = await self._doc_repo.get_doc(doc_id)
        if doc is None:
            raise ValueError(f"Documentation {doc_id} not found.")

        return DocumentationResponse(
            id=doc.id,
            repository_id=doc.repository_id,
            doc_type=doc.doc_type,
            title=doc.title,
            content=doc.content,
            file_path=doc.file_path,
            status=doc.status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    async def update_documentation(
        self,
        doc_id: UUID,
        request: DocUpdateRequest,
    ) -> DocumentationResponse:
        """Update documentation content or title."""
        doc = await self._doc_repo.update_doc_content(
            doc_id=doc_id,
            content=request.content,
            title=request.title,
        )
        if doc is None:
            raise ValueError(f"Documentation {doc_id} not found.")
        await self._db.commit()

        return DocumentationResponse(
            id=doc.id,
            repository_id=doc.repository_id,
            doc_type=doc.doc_type,
            title=doc.title,
            content=doc.content,
            file_path=doc.file_path,
            status=doc.status,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    async def delete_documentation(self, doc_id: UUID) -> bool:
        """Delete documentation record."""
        deleted = await self._doc_repo.delete_doc(doc_id)
        await self._db.commit()
        return deleted > 0

    async def _synthesize_doc(
        self,
        repo_name: str,
        doc_type: DocType,
        files: list,
        symbols: list,
        imports: list,
        custom_title: str | None,
        custom_instructions: str | None,
    ) -> tuple[str, str, str]:
        """Generate structured Markdown documentation based on doc_type."""
        file_paths = [f.relative_path for f in files]
        languages = list({f.language for f in files if f.language})
        export_symbols = [s for s in symbols if s.visibility in ("public", "export")]

        if doc_type == DocType.readme:
            title = custom_title or f"README — {repo_name}"
            file_path = "README.md"
            content = self._generate_readme_md(
                repo_name, file_paths, languages, export_symbols, custom_instructions
            )
        elif doc_type == DocType.architecture:
            title = custom_title or f"Architecture & Component Guide — {repo_name}"
            file_path = "docs/ARCHITECTURE.md"
            content = self._generate_architecture_md(
                repo_name, file_paths, languages, symbols, imports, custom_instructions
            )
        elif doc_type == DocType.api_reference:
            title = custom_title or f"API & Code Reference — {repo_name}"
            file_path = "docs/API_REFERENCE.md"
            content = self._generate_api_reference_md(
                repo_name, export_symbols, custom_instructions
            )
        else:
            title = custom_title or f"Technical Guide — {repo_name}"
            file_path = "docs/GUIDE.md"
            content = f"# {title}\n\nTechnical overview of `{repo_name}` codebase.\n"

        return title, content, file_path

    def _generate_readme_md(
        self,
        repo_name: str,
        file_paths: list[str],
        languages: list[str],
        export_symbols: list,
        custom_instructions: str | None,
    ) -> str:
        """Generate comprehensive README.md."""
        lang_str = ", ".join(languages) if languages else "Polyglot"
        tree_preview = "\n".join([f"- `{p}`" for p in file_paths[:15]])
        if len(file_paths) > 15:
            tree_preview += f"\n- *(and {len(file_paths) - 15} more files)*"

        symbols_table = "\n".join(
            [
                f"| `{s.name}` | `{s.symbol_type}` | `{s.file_id}` | L{s.start_line}-{s.end_line} |"
                for s in export_symbols[:10]
            ]
        )
        if not symbols_table:
            symbols_table = "| (No public exported symbols indexed) | - | - | - |"

        instructions_section = (
            f"\n> **Custom Focus**: {custom_instructions}\n" if custom_instructions else ""
        )

        return f"""# {repo_name}

{instructions_section}
## Overview
`{repo_name}` is a software repository containing **{len(file_paths)} source files** written primarily in **{lang_str}**.

---

## Tech Stack & Languages
- **Primary Languages**: {lang_str}
- **Indexed Source Files**: {len(file_paths)}
- **Extracted AST Symbols**: {len(export_symbols)} Public Exports

---

## Repository Structure Overview
{tree_preview}

---

## Key Exported Code Symbols & Components
| Symbol Name | Type | File ID | Location |
| :--- | :--- | :--- | :--- |
{symbols_table}

---

## Getting Started

### Installation & Prerequisites
1. Ensure required language runtime environment ({lang_str}) is installed.
2. Clone repository locally and run build scripts.

```bash
# Example setup
git clone <repository_url>
cd {repo_name}
```

*Auto-generated by ForgeAI Technical Documentation Engine.*
"""

    def _generate_architecture_md(
        self,
        repo_name: str,
        file_paths: list[str],
        languages: list[str],
        symbols: list,
        imports: list,
        custom_instructions: str | None,
    ) -> str:
        """Generate ARCHITECTURE.md."""
        modules = list({p.split("/")[0] if "/" in p else p for p in file_paths})
        modules_list = "\n".join([f"- **`/{m}`**: Module containing core functionality." for m in modules[:10]])

        return f"""# Architecture & Component Specification — {repo_name}

## System Overview
The `{repo_name}` codebase is structured into **{len(modules)} high-level modules** across **{len(file_paths)} source files**.

---

## High-Level Module Hierarchy
{modules_list}

---

## Key Architectural Components & AST Symbol Table
Total AST symbols extracted: **{len(symbols)}**.
Total module import dependencies tracked: **{len(imports)}**.

### Component Dependencies
- Extracted AST symbols register clear parent-child structural boundaries.
- Cross-module dependencies are resolved via Tree-sitter import statement tracking.

---

## Design Patterns & Conventions
- Modular separation of concerns across service layers and data contracts.
- Strongly-typed Pydantic / TypeScript data transfer objects.

*Auto-generated by ForgeAI Technical Documentation Engine.*
"""

    def _generate_api_reference_md(
        self,
        repo_name: str,
        export_symbols: list,
        custom_instructions: str | None,
    ) -> str:
        """Generate API_REFERENCE.md."""
        if not export_symbols:
            symbols_block = "*(No public exported API functions or classes were indexed in this repository.)*"
        else:
            blocks = []
            for s in export_symbols[:20]:
                doc_str = f"\n  *{s.docstring.strip()}*" if getattr(s, "docstring", None) else ""
                blocks.append(
                    f"### `{s.name}`\n"
                    f"- **Type**: `{s.symbol_type}`\n"
                    f"- **Location**: Lines {s.start_line}-{s.end_line}\n"
                    f"- **Signature**: `{getattr(s, 'signature', s.name)}`"
                    f"{doc_str}\n"
                )
            symbols_block = "\n".join(blocks)

        return f"""# API & Code Reference — {repo_name}

This document contains auto-extracted API specifications for exported functions, classes, and types in `{repo_name}`.

---

## Public Exported Symbols ({len(export_symbols)})

{symbols_block}

---

*Auto-generated by ForgeAI Technical Documentation Engine.*
"""
