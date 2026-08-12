"""ForgeAI models package.

ORM models are added here incrementally:
  Phase 2: repository.py, file.py  ✓
  Phase 3: symbol.py, import_.py   ✓
  Phase 4: embedding.py            ✓
  Phase 6: conversation.py
  Phase 9: documentation.py

Importing this package is sufficient for Alembic autogenerate and
SQLAlchemy relationship resolution -- all models register themselves
against ``Base.metadata`` on import.
"""

from forgeai.models.embedding import ChunkType, CodeEmbedding
from forgeai.models.file import RepositoryFile
from forgeai.models.import_ import Import, ImportType
from forgeai.models.repository import Repository, RepositoryStatus
from forgeai.models.symbol import Symbol, SymbolType, Visibility

__all__ = [
    "ChunkType",
    "CodeEmbedding",
    "Import",
    "ImportType",
    "Repository",
    "RepositoryFile",
    "RepositoryStatus",
    "Symbol",
    "SymbolType",
    "Visibility",
]
