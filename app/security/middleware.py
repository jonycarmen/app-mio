from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.types import ASGIApp

from app.security.auth import get_session
from app.security.user_auth import get_user_session
from app.security.logging import security_logger


# ---------------------------------------------------------------------------
# Default settings object (used as fallback when DB has no row)
# ---------------------------------------------------------------------------
class _DefaultSettings:
    app_name = "People Manager"
    logo_path = None
    primary_color = "#6366f1"
    secondary_color = "#3563e9"
    welcome_text = None


class AppSettingsMiddleware(BaseHTTPMiddleware):
    """Loads AppSettings row (id=1) from DB on every request and stores in request.state."""

    _SKIP_PREFIXES = ("/static/", "/favicon.ico", "/branding/")

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in self._SKIP_PREFIXES):
            request.state.app_settings = _DefaultSettings()
            return await call_next(request)

        from app.db import SessionLocal
        from app.models.app_settings import AppSettings

        db = SessionLocal()
        try:
            s = db.get(AppSettings, 1)
            request.state.app_settings = s if s else _DefaultSettings()
        except Exception:
            request.state.app_settings = _DefaultSettings()
        finally:
            db.close()

        return await call_next(request)


# Routes that do NOT require admin authentication
_ADMIN_PUBLIC_PREFIXES = (
    "/form/",
    "/static/",
    "/admin/login",
    "/admin/logout",
    "/admin/forgot-password",
    "/admin/verify-code",
    "/admin/reset-password",
    "/register/",
    "/i/",
    "/user/login",
    "/user/logout",
    "/login",
    "/acceso",
    "/portal/",
    "/favicon.ico",
)

# Routes protected by UserAuthMiddleware (not by AdminAuthMiddleware)
_USER_PROTECTED_PREFIXES = ("/portal/",)


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Protects all /admin/* and other admin routes except public ones."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Always allow public paths
        if any(path.startswith(p) for p in _ADMIN_PUBLIC_PREFIXES):
            return await call_next(request)

        # Check admin session
        session = get_session(request)
        if not session:
            ip = _get_ip(request)
            security_logger.warning("ADMIN_UNAUTH | ip=%s | path=%s", ip, path)

            if path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "Authentication required"},
                    status_code=401,
                )
            return RedirectResponse(f"/admin/login?next={path}", status_code=302)

        return await call_next(request)


class UserAuthMiddleware(BaseHTTPMiddleware):
    """Protects /portal/* routes — requires user session."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if not any(path.startswith(p) for p in _USER_PROTECTED_PREFIXES):
            return await call_next(request)

        session = get_user_session(request)
        if not session:
            ip = _get_ip(request)
            security_logger.warning("USER_UNAUTH | ip=%s | path=%s", ip, path)
            return RedirectResponse(f"/user/login?next={path}", status_code=302)

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security-related HTTP response headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        )
        return response


def _get_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
