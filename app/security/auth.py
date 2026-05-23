import secrets
from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import settings
from app.security.logging import security_logger

SESSION_COOKIE_NAME = "admin_session"
CSRF_COOKIE_NAME = "csrf_token"
SESSION_MAX_AGE = 86400 * 7  # 7 days

# Recovery flow cookie names
RESET_PENDING_COOKIE = "pwd_reset_pending"   # after forgot-password: holds admin_id
RESET_VERIFIED_COOKIE = "pwd_reset_verified"  # after verify-code: holds admin_id
VERIFY_ATTEMPTS_COOKIE = "pwd_verify_attempts"  # tracks failed code attempts


# ---------------------------------------------------------------------------
# Signers
# ---------------------------------------------------------------------------

def _get_signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.admin_secret_key, salt="admin-session")


def _get_reset_signer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.admin_secret_key, salt=salt)


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def create_session_token(username: str) -> str:
    """Create a signed session token for the given admin username."""
    return _get_signer().dumps({"user": username})


def verify_session_token(token: str) -> dict | None:
    """Verify and decode the session token. Returns payload dict or None."""
    try:
        return _get_signer().loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_session(request: Request) -> dict | None:
    """Extract and verify the admin session from cookies."""
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return None
    return verify_session_token(cookie)


def require_admin(request: Request) -> dict:
    """FastAPI dependency: raises 401 if admin session is invalid."""
    session = get_session(request)
    if not session:
        security_logger.warning("ADMIN_UNAUTH | ip=%s | path=%s", _get_ip(request), request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return session


# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Admin DB authentication
# ---------------------------------------------------------------------------

def get_admin_by_username(username: str, db: Session):
    """Return Admin row by username, or None."""
    from app.models.admin import Admin
    return db.query(Admin).filter(Admin.username == username).first()


def verify_admin_login(username: str, password: str, db: Session) -> bool:
    """Verify admin credentials against the DB (bcrypt). Falls back to env if no DB admins."""
    admin = get_admin_by_username(username, db)
    if admin:
        return verify_password(password, admin.password_hash)
    # Fallback: compare against .env values (for first-run before migration)
    valid_user = secrets.compare_digest(username.encode(), settings.admin_username.encode())
    valid_pass = secrets.compare_digest(password.encode(), settings.admin_password.encode())
    return valid_user and valid_pass


def check_admin_credentials(username: str, password: str) -> bool:
    """Legacy constant-time comparison against .env credentials (kept for compatibility)."""
    valid_user = secrets.compare_digest(username.encode(), settings.admin_username.encode())
    valid_pass = secrets.compare_digest(password.encode(), settings.admin_password.encode())
    return valid_user and valid_pass


def ensure_default_admin(db: Session) -> None:
    """Create default admin from .env if no admins exist in the database."""
    from app.models.admin import Admin

    if db.query(Admin).count() == 0:
        admin = Admin(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
        )
        db.add(admin)
        db.commit()
        security_logger.info("DEFAULT_ADMIN_CREATED | username=%s", settings.admin_username)


# ---------------------------------------------------------------------------
# CSRF helpers
# ---------------------------------------------------------------------------

def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return secrets.token_hex(32)


# ---------------------------------------------------------------------------
# Recovery flow cookie helpers
# ---------------------------------------------------------------------------

def create_reset_pending_token(admin_id: int) -> str:
    """Signed token stored in cookie after forgot-password step."""
    return _get_reset_signer("pwd-reset-pending").dumps({"admin_id": admin_id})


def verify_reset_pending_token(token: str) -> dict | None:
    """Verify reset-pending cookie. Valid for 15 minutes."""
    try:
        return _get_reset_signer("pwd-reset-pending").loads(token, max_age=900)
    except (BadSignature, SignatureExpired):
        return None


def create_reset_verified_token(admin_id: int) -> str:
    """Signed token stored in cookie after successful code verification."""
    return _get_reset_signer("pwd-reset-verified").dumps({"admin_id": admin_id})


def verify_reset_verified_token(token: str) -> dict | None:
    """Verify reset-verified cookie. Valid for 10 minutes."""
    try:
        return _get_reset_signer("pwd-reset-verified").loads(token, max_age=600)
    except (BadSignature, SignatureExpired):
        return None


def create_verify_attempts_token(admin_id: int, count: int) -> str:
    """Signed token tracking verification attempts."""
    return _get_reset_signer("pwd-verify-attempts").dumps({"admin_id": admin_id, "count": count})


def get_verify_attempts(request: Request, admin_id: int) -> int:
    """Return current attempt count for this admin_id from cookie (0 if absent/invalid)."""
    cookie = request.cookies.get(VERIFY_ATTEMPTS_COOKIE)
    if not cookie:
        return 0
    try:
        payload = _get_reset_signer("pwd-verify-attempts").loads(cookie, max_age=900)
        if payload.get("admin_id") == admin_id:
            return int(payload.get("count", 0))
    except (BadSignature, SignatureExpired):
        pass
    return 0


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _get_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
