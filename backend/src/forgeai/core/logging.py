"""Structured logging configuration using structlog.

Configures structlog with JSON output in production and human-readable
console output in development. Call configure_logging() once at startup
before any loggers are created.
"""

import logging
import sys

import structlog


def configure_logging(*, debug: bool = True) -> None:
    """Configure structlog for the application.

    Args:
        debug: If True, use pretty console output. If False, use JSON.
    """
    # Use stdlib logger factory so add_logger_name can access logger.name
    logger_factory = structlog.stdlib.LoggerFactory()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if debug:
        # Development: human-readable, colorized console output
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: machine-parseable JSON
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=logger_factory,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib root logger to route through structlog at same level
    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG if debug else logging.INFO,
        stream=sys.stdout,
    )
