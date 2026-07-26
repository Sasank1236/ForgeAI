"""ForgeAI schemas package.

Pydantic DTOs (Data Transfer Objects) are added here incrementally:
  Phase 2: repository.py  ✓
  Phase 3: symbol.py, import_.py, parser.py  ✓
  Phase 5: search.py
  Phase 6: chat.py
  Phase 7: plan.py
"""

# Phase 2
from forgeai.schemas.repository import (
    ImportRequest,
    ImportResponse,
    RepositoryStats,
    RepositoryResponse,
    RepositoryListItem,
    FileResponse,
    FilesListResponse,
)

# Phase 3
from forgeai.schemas.symbol import (
    SymbolResponse,
    SymbolListResponse,
    SymbolFilter,
)
from forgeai.schemas.import_ import (
    ImportRecordResponse,
    ImportListResponse,
    ImportFilter,
)
from forgeai.schemas.parser import (
    ParseRequest,
    ParseResponse,
    ParseStatsResponse,
    LanguageParseStats,
)

__all__ = [
    # Phase 2
    "ImportRequest",
    "ImportResponse",
    "RepositoryStats",
    "RepositoryResponse",
    "RepositoryListItem",
    "FileResponse",
    "FilesListResponse",
    # Phase 3 — symbols
    "SymbolResponse",
    "SymbolListResponse",
    "SymbolFilter",
    # Phase 3 — imports
    "ImportRecordResponse",
    "ImportListResponse",
    "ImportFilter",
    # Phase 3 — parser
    "ParseRequest",
    "ParseResponse",
    "ParseStatsResponse",
    "LanguageParseStats",
]
