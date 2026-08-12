"""ForgeAI repositories package.

Data access layer (DAL) objects are added here incrementally:
  Phase 2: repository_repo.py, file_repo.py  ✓
  Phase 3: symbol_repo.py, import_repo.py    ✓
  Phase 4: embedding_repo.py                ✓
"""

# Phase 2
from forgeai.repositories.file_repo import FileRepo
from forgeai.repositories.repository_repo import RepositoryRepo

# Phase 3
from forgeai.repositories.import_repo import ImportRepo
from forgeai.repositories.symbol_repo import SymbolRepo

# Phase 4
from forgeai.repositories.embedding_repo import EmbeddingRepo

__all__ = [
    "EmbeddingRepo",
    "FileRepo",
    "ImportRepo",
    "RepositoryRepo",
    "SymbolRepo",
]
