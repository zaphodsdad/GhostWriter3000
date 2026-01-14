"""Middleware modules."""

from app.middleware.auth import api_key_auth_middleware

__all__ = ["api_key_auth_middleware"]
