"""ForgeAI application configuration.

All settings are loaded from environment variables (or .env file).
Access settings via the get_settings() cached singleton.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings, resolved from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ─────────────────────────────────────────────────────────
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=True)
    secret_key: str = Field(default="change_this_in_production")

    # ─── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://forgeai:forgeai_dev@localhost:5432/forgeai"
    )

    # ─── Redis ────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ─── OpenAI ───────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="")

    # ─── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="openai")
    llm_model: str = Field(default="gpt-4o")
    llm_max_tokens: int = Field(default=4096)
    llm_temperature: float = Field(default=0.1)

    # ─── Embeddings ───────────────────────────────────────────────────────────
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536)

    # ─── Repository Limits ────────────────────────────────────────────────────
    max_repo_size_mb: int = Field(default=500)
    max_file_count: int = Field(default=10_000)
    max_file_size_kb: int = Field(default=500)

    # ─── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: Annotated[list[str], Field(default=["http://localhost:3000"])]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        """Allow comma-separated string from env or a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
