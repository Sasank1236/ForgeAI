"""Async Redis client with lazy initialization.

Usage (in FastAPI route):
    async def my_route(cache: Redis = Depends(get_redis)):
        await cache.set("key", "value", ex=300)
"""

from collections.abc import AsyncGenerator

import redis.asyncio as redis

from forgeai.config import get_settings

settings = get_settings()

# ─── Client Pool ──────────────────────────────────────────────────────────────
# A single connection pool is shared across the application lifetime.
# decode_responses=True returns str instead of bytes for all responses.
_pool: redis.ConnectionPool | None = None
_client: redis.Redis | None = None


def _get_pool() -> redis.ConnectionPool:
    """Return (or lazily create) the shared connection pool."""
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _pool


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """FastAPI dependency that yields a Redis client from the shared pool."""
    client: redis.Redis = redis.Redis(connection_pool=_get_pool())
    try:
        yield client
    finally:
        await client.aclose()


async def close_redis_pool() -> None:
    """Disconnect all Redis connections. Call during application shutdown."""
    global _pool, _client
    if _pool:
        await _pool.aclose()
        _pool = None
    _client = None
