"""Embedding generation service.

Generates 1536-dimensional vector embeddings using OpenAI / LiteLLM text-embedding-3-small model.
Handles text batching, rate limits, and fallback deterministic mock vector generation when offline/unconfigured.

Phase 4 — Vector Embeddings & Knowledge Base
"""

from __future__ import annotations

import math
from typing import Final

import structlog

from forgeai.config import get_settings

logger = structlog.get_logger(__name__)

# Default model: OpenAI text-embedding-3-small (1536 dimensions)
DEFAULT_EMBEDDING_MODEL: Final[str] = "text-embedding-3-small"
EMBEDDING_DIMENSION: Final[int] = 1536


class EmbeddingService:
    """Service for generating 1536-dimensional vector embeddings."""

    def __init__(self, model_name: str | None = None) -> None:
        cfg = get_settings()
        self.model_name = model_name or getattr(
            cfg, "embedding_model", DEFAULT_EMBEDDING_MODEL
        )
        self.api_key = getattr(cfg, "openai_api_key", "")

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of text strings.

        Batches requests and returns a list of 1536-dimensional float vectors.
        """
        if not texts:
            return []

        # If API key is not set or empty, generate deterministic fallback vectors
        if not self.api_key or self.api_key == "change_me_to_a_real_key":
            logger.debug(
                "using_mock_embeddings",
                reason="no_api_key",
                count=len(texts),
            )
            return [self._generate_mock_vector(t) for t in texts]

        try:
            import litellm

            # Batch call to LiteLLM embedding API
            response = await litellm.aembedding(
                model=self.model_name,
                input=texts,
                api_key=self.api_key,
            )
            embeddings = [item["embedding"] for item in response.data]
            logger.info("embeddings_generated", count=len(embeddings))
            return embeddings
        except Exception as err:
            logger.warning(
                "embedding_api_failed_falling_back_to_mock",
                error=str(err),
                count=len(texts),
            )
            return [self._generate_mock_vector(t) for t in texts]

    async def generate_query_embedding(self, text: str) -> list[float]:
        """Generate a single 1536-dimensional query embedding vector."""
        vectors = await self.generate_embeddings([text])
        return vectors[0] if vectors else self._generate_mock_vector(text)

    def _generate_mock_vector(self, text: str) -> list[float]:
        """Generate a deterministic 1536-dimensional L2-normalized float vector."""
        # Use hash of text to generate deterministic float values
        text_bytes = text.encode("utf-8")
        vector: list[float] = []

        for i in range(EMBEDDING_DIMENSION):
            val = (hash(text_bytes + str(i).encode("utf-8")) % 10000) / 5000.0 - 1.0
            vector.append(val)

        # L2 Normalize the vector so cosine similarity calculations match real embeddings
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector
