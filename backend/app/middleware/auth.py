"""API key authentication middleware."""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.

    If API_AUTH_KEY is set in .env, requires X-API-Key header on all /api/ routes.
    If API_AUTH_KEY is empty, no authentication is required (local dev mode).
    Health endpoint is always accessible.
    """

    # Paths that don't require authentication
    PUBLIC_PATHS = [
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip auth if no API key is configured
        if not settings.api_auth_key:
            return await call_next(request)

        # Skip auth for public paths
        path = request.url.path
        if any(path.startswith(public) for public in self.PUBLIC_PATHS):
            return await call_next(request)

        # Skip auth for static files (frontend)
        if not path.startswith("/api/"):
            return await call_next(request)

        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="Missing X-API-Key header"
            )

        if api_key != settings.api_auth_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )

        return await call_next(request)


# Convenience function for adding to app
def api_key_auth_middleware(app):
    """Add API key authentication middleware to FastAPI app."""
    app.add_middleware(APIKeyAuthMiddleware)
