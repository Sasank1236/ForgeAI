"""ForgeAI domain exception hierarchy.

All application-specific exceptions live here. Routers translate these
into appropriate HTTP responses — business logic never imports HTTPException.
"""

from http import HTTPStatus


class ForgeAIError(Exception):
    """Base class for all ForgeAI application errors."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


# ─── 400 Bad Request ──────────────────────────────────────────────────────────
class ValidationError(ForgeAIError):
    status_code = HTTPStatus.BAD_REQUEST.value
    detail = "Validation failed."


class InvalidRepositoryPathError(ForgeAIError):
    status_code = HTTPStatus.BAD_REQUEST.value
    detail = "The provided repository path is invalid or does not exist."


class RepositoryTooLargeError(ForgeAIError):
    status_code = HTTPStatus.BAD_REQUEST.value
    detail = "Repository exceeds the maximum allowed size."


# ─── 404 Not Found ────────────────────────────────────────────────────────────
class NotFoundError(ForgeAIError):
    status_code = HTTPStatus.NOT_FOUND.value
    detail = "Resource not found."


class RepositoryNotFoundError(NotFoundError):
    detail = "Repository not found."


# ─── 409 Conflict ─────────────────────────────────────────────────────────────
class ConflictError(ForgeAIError):
    status_code = HTTPStatus.CONFLICT.value
    detail = "Resource conflict."


class RepositoryAlreadyExistsError(ConflictError):
    detail = "A repository with this path is already imported."


# ─── 422 Unprocessable ────────────────────────────────────────────────────────
class ParseError(ForgeAIError):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY.value
    detail = "Failed to parse repository."


# ─── 503 Service Unavailable ─────────────────────────────────────────────────
class LLMError(ForgeAIError):
    status_code = HTTPStatus.SERVICE_UNAVAILABLE.value
    detail = "LLM service is unavailable."


class EmbeddingError(ForgeAIError):
    status_code = HTTPStatus.SERVICE_UNAVAILABLE.value
    detail = "Embedding service is unavailable."
