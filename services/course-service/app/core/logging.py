"""
Structured Logging Configuration.

Provides JSON-formatted logging with:
- Correlation ID tracking for request tracing
- Log levels based on environment
- Sensitive data sanitization
- Request/response logging middleware
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from app.core.config import settings
from loguru import logger

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record):
        record.correlation_id = correlation_id_var.get()
        return True


class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to loguru."""

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# Sensitive fields to sanitize in logs
SENSITIVE_FIELDS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "authorization",
    "credit_card",
    "card_number",
    "cvv",
    "ssn",
}


def sanitize_data(data: Any, depth: int = 0) -> Any:
    """
    Recursively sanitize sensitive data from logs.

    Args:
        data: Data to sanitize
        depth: Current recursion depth (max 10)

    Returns:
        Sanitized data
    """
    if depth > 10:
        return data

    if isinstance(data, dict):
        return {
            k: (
                "***REDACTED***"
                if k.lower() in SENSITIVE_FIELDS
                else sanitize_data(v, depth + 1)
            )
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_data(item, depth + 1) for item in data]
    elif isinstance(data, str) and len(data) > 100:
        # Truncate very long strings
        return data[:100] + "..."
    return data


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for the current context."""
    cid = correlation_id or str(uuid.uuid4())[:8]
    correlation_id_var.set(cid)
    return cid


def format_log_record(record: Dict) -> str:
    """Format log record with correlation ID."""
    correlation_id = correlation_id_var.get() or "-"

    # JSON format for production
    if settings.ENVIRONMENT == "production":
        return (
            "{{"
            '"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
            '"level":"{level}",'
            f'"correlation_id":"{correlation_id}",'
            '"service":"{extra[service]}",'
            '"module":"{name}",'
            '"function":"{function}",'
            '"line":{line},'
            '"message":"{message}"'
            "}}\n"
        )
    else:
        # Pretty format for development
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            f"<yellow>[{correlation_id}]</yellow> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>\n"
        )


def setup_logging(service_name: str = "course-service"):
    """
    Configure structured logging for the application.

    Args:
        service_name: Name of the service for log identification

    Returns:
        Configured logger instance
    """
    # Remove default logger
    logger.remove()

    # Configure logger with correlation ID support
    logger.configure(extra={"service": service_name})

    # Add custom logger
    logger.add(
        sys.stdout,
        format=format_log_record,
        level=settings.LOG_LEVEL,
        serialize=settings.ENVIRONMENT == "production",
        colorize=settings.ENVIRONMENT != "production",
        enqueue=True,  # Thread-safe logging
    )

    # Add file logging for production
    if settings.ENVIRONMENT == "production":
        logger.add(
            f"/var/log/{service_name}/{service_name}.log",
            rotation="100 MB",
            retention="30 days",
            compression="gz",
            format=format_log_record,
            level=settings.LOG_LEVEL,
            serialize=True,
        )

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    for logger_name in (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
    ):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]

    return logger


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    extra: Optional[Dict] = None,
):
    """
    Log API request with structured format.

    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: Optional user ID
        extra: Optional extra fields
    """
    log_data = {
        "event": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "correlation_id": get_correlation_id(),
    }

    if user_id:
        log_data["user_id"] = user_id

    if extra:
        log_data.update(sanitize_data(extra))

    if status_code >= 500:
        logger.error(
            f"Request: {method} {path} -> {status_code} ({duration_ms:.2f}ms)",
            **log_data,
        )
    elif status_code >= 400:
        logger.warning(
            f"Request: {method} {path} -> {status_code} ({duration_ms:.2f}ms)",
            **log_data,
        )
    else:
        logger.info(
            f"Request: {method} {path} -> {status_code} ({duration_ms:.2f}ms)",
            **log_data,
        )


def log_service_call(
    service: str,
    method: str,
    path: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
):
    """
    Log inter-service communication.

    Args:
        service: Target service name
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        error: Optional error message
    """
    log_data = {
        "event": "service_call",
        "target_service": service,
        "method": method,
        "path": path,
        "correlation_id": get_correlation_id(),
    }

    if status_code:
        log_data["status_code"] = status_code
    if duration_ms:
        log_data["duration_ms"] = round(duration_ms, 2)
    if error:
        log_data["error"] = error
        logger.error(
            f"Service call to {service}: {method} {path} failed - {error}",
            **log_data,
        )
    else:
        logger.info(
            f"Service call to {service}: {method} {path} -> {status_code}",
            **log_data,
        )


def log_business_event(
    event_type: str,
    event_data: Dict,
    user_id: Optional[str] = None,
):
    """
    Log business events (enrollments, payments, etc.).

    Args:
        event_type: Type of business event
        event_data: Event data
        user_id: Optional user ID
    """
    log_data = {
        "event": "business_event",
        "event_type": event_type,
        "correlation_id": get_correlation_id(),
        **sanitize_data(event_data),
    }

    if user_id:
        log_data["user_id"] = user_id

    logger.info(f"Business event: {event_type}", **log_data)


# Export logging utilities
__all__ = [
    "setup_logging",
    "logger",
    "get_correlation_id",
    "set_correlation_id",
    "sanitize_data",
    "log_request",
    "log_service_call",
    "log_business_event",
    "correlation_id_var",
]
