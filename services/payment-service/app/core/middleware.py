"""
Logging Middleware for FastAPI.

Provides automatic request/response logging with:
- Correlation ID propagation
- Request timing
- Structured logging
"""

import time
import uuid
from typing import Callable

from app.core.logging import log_request, logger, set_correlation_id
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and log details."""
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())[:8]
        set_correlation_id(correlation_id)

        # Start timing
        start_time = time.time()

        # Get user ID if available
        user_id = request.headers.get("x-user-id")

        # Log incoming request
        logger.debug(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "event": "request_start",
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "user_id": user_id,
                "correlation_id": correlation_id,
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "event": "request_error",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                    "correlation_id": correlation_id,
                },
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Log response (skip health checks to reduce noise)
        if request.url.path not in ["/health", "/ready", "/metrics"]:
            log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
            )

        return response
