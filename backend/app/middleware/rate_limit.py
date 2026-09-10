import time
import logging
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("findit.middleware.ratelimit")

RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 60  # max 60 requests per minute per IP

SENSITIVE_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/items",
    "/api/v1/items/form",
}

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_timestamps: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "127.0.0.1"
        path = request.url.path

        # Apply rate limiting to POST / PUT / PATCH endpoints or sensitive paths
        is_sensitive = request.method in ("POST", "PUT", "PATCH") and (
            path in SENSITIVE_PATHS or "/messages" in path or "/analyze" in path
        )

        if is_sensitive:
            now = time.time()
            timestamps = self.request_timestamps[client_ip]

            # Prune old timestamps
            timestamps = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW]
            self.request_timestamps[client_ip] = timestamps

            if len(timestamps) >= MAX_REQUESTS_PER_WINDOW:
                logger.warning(f"Rate limit exceeded for IP {client_ip} on path {path}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please wait a minute before trying again."}
                )

            timestamps.append(now)

        return await call_next(request)
