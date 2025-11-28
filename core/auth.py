"""Authentication Middleware for resolving user info from authorization header."""

from typing import Optional as Opt
import jwt
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.settings import get_settings


class AuthInfo:
    """Holds authentication information resolved from JWT token."""

    def __init__(
        self,
        user_id: Opt[str] = None,
        session_id: Opt[str] = None,
        role: Opt[str] = None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.role = role

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to resolve auth info from authorization header."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        auth_info = AuthInfo()

        authorization = request.headers.get("authorization")
        if authorization:
            try:
                scheme, token = authorization.split(" ", 1)
                if scheme.lower() == "bearer":
                    payload = jwt.decode(
                        token,
                        settings.auth.jwt_secret_key,
                        algorithms=settings.auth.jwt_algorithms,
                        audience=settings.auth.jwt_allowed_audiences,
                    )
                    auth_info = AuthInfo(
                        user_id=payload.get("sub"),
                        session_id=payload.get("session_id"),
                        role=payload.get("role"),
                    )
            except (ValueError, jwt.InvalidTokenError):
                pass

        request.state.auth = auth_info
        response = await call_next(request)
        return response


def get_current_user(request: Request) -> AuthInfo:
    """FastAPI dependency to get current authenticated user."""
    auth: AuthInfo = getattr(request.state, "auth", AuthInfo())
    return auth


def require_auth(request: Request) -> AuthInfo:
    """FastAPI dependency that requires authentication."""
    auth = get_current_user(request)
    if not auth.is_authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return auth
