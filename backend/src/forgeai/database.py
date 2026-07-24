"""Async SQLAlchemy database engine and session factory.

Usage (in FastAPI route):
    async def my_route(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(MyModel))
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from forgeai.config import get_settings

settings = get_settings()

# ─── Engine ───────────────────────────────────────────────────────────────────
# pool_pre_ping=True verifies connections before using them, preventing stale
# connection errors after database restarts.
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# ─── Session Factory ──────────────────────────────────────────────────────────
# expire_on_commit=False prevents lazy-loading errors after commit in async
# context where the session may be closed.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─── Declarative Base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# ─── Dependency ───────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a transactional database session.

    Automatically rolls back on exception and always closes the session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
