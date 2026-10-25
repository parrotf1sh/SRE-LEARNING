import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("task_api.middleware")


async def request_logging_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    response.headers["X-Request-ID"] = request_id

    path = request.url.path
    status_code = response.status_code

    if path == "/health":
        if status_code >= 500:
            logger.warning(
                "Health check failed: %s %s %s (%.2fms)",
                request.method,
                path,
                status_code,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
    else:
        log_level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR
        getattr(logger, log_level)(
            "%s %s %s (%.2fms)",
            request.method,
            path,
            status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

    return response
