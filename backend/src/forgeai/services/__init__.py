"""ForgeAI services package.

Business logic services are added here incrementally:
  Phase 2: scanner.py, repository_service.py  ✓
  Phase 3: parser.py
  Phase 4: embedding.py, knowledge_base.py
  Phase 5: search.py
  Phase 6: context_builder.py, llm.py, chat.py
  Phase 7: task_planner.py, code_suggestion.py
  Phase 8: documentation.py
"""

# Phase 2
from forgeai.services.scanner import RepositoryScanner
from forgeai.services.repository_service import RepositoryService

__all__ = ["RepositoryScanner", "RepositoryService"]
