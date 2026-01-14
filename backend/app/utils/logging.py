"""Structured logging configuration."""

import logging
import sys
from datetime import datetime
from typing import Any
import json

from app.config import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "generation_id"):
            log_data["generation_id"] = record.generation_id
        if hasattr(record, "scene_id"):
            log_data["scene_id"] = record.scene_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """
    Configure structured logging for the application.

    Returns:
        Configured root logger
    """
    # Get log level from settings
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create formatter
    formatter = JSONFormatter()

    # Configure handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Configure uvicorn loggers to use same format
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding extra fields to log records."""

    def __init__(self, logger: logging.Logger, **kwargs: Any):
        self.logger = logger
        self.extra = kwargs

    def info(self, message: str, **kwargs: Any):
        extra = {**self.extra, **kwargs}
        self.logger.info(message, extra=extra)

    def error(self, message: str, **kwargs: Any):
        extra = {**self.extra, **kwargs}
        self.logger.error(message, extra=extra)

    def warning(self, message: str, **kwargs: Any):
        extra = {**self.extra, **kwargs}
        self.logger.warning(message, extra=extra)

    def debug(self, message: str, **kwargs: Any):
        extra = {**self.extra, **kwargs}
        self.logger.debug(message, extra=extra)
