"""User session authentication (separate from admin session)."""
import secrets

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from fastapi import Request

from app.config import settings
from app.security.logging import security_logger

USER_SESSION_COOKIE_NAME = "user_session"
USER_SESSION_MAX_AGE = 86400 * 30  # 30 days


def _get_user_signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.admin_secret_key, salt="user-session")


def create_user_session_token(user_id: int) -> str:
    return _get_user_signer().dumps({"user_id": user_id})


def verify_user_session_token(token: str) -> dict | None:
    try:
        return _get_user_signer().loads(token, max_age=USER_SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_user_session(request: Request) -> dict | None:
    cookie = request.cookies.get(USER_SESSION_COOKIE_NAME)
    if not cookie:
        return None
    return verify_user_session_token(cookie)


def get_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
