import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import models  # noqa: F401 — importar modelos para que SQLAlchemy los registre
import app.routers.public_forms as public_forms
from app.db import SessionLocal
from app.routers.api import documents, payrolls, people
from app.routers.password_recovery import router as recovery_router
from app.routers.portal import router as portal_router
from app.routers.user_auth import router as user_auth_router
from app.routers.web import pages
from app.routers.web.admin_settings import router as admin_settings_router
from app.routers.web.admin_users import router as admin_users_router
from app.routers.web.backups import router as backups_router
from app.security.auth import (
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    create_session_token,
    ensure_default_admin,
    generate_csrf_token,
    get_session,
    verify_admin_login,
)
from app.security.logging import security_logger
from app.security.middleware import AdminAuthMiddleware, SecurityHeadersMiddleware, UserAuthMiddleware, AppSettingsMiddleware
from app.security.rate_limiter import limiter
from app.security.user_auth import get_user_session

Path("storage/pdfs").mkdir(parents=True, exist_ok=True)
Path("storage/profiles").mkdir(parents=True, exist_ok=True)
Path("storage/branding").mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create default admin on startup if none exist."""
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()
    from app.services.backup_service import start_auto_backup, stop_auto_backup
    start_auto_backup()
    yield
    stop_auto_backup()


app = FastAPI(title="People PDF Payroll Manager", lifespan=lifespan)

# ── Slowapi rate limiting ────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Custom security middlewares (order: outermost = last added) ──────────────
app.add_middleware(UserAuthMiddleware)
app.add_middleware(AdminAuthMiddleware)
app.add_middleware(AppSettingsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# ── Static files ─────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── Jinja2 templates for login ────────────────────────────────────────────────
_templates = Jinja2Templates(directory="app/templates")


def _get_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Admin login / logout ──────────────────────────────────────────────────────
@app.get("/admin/login", response_class=HTMLResponse, include_in_schema=False)
def admin_login_page(request: Request, next: str = "/people", reset: str = ""):
    # Already logged in → redirect (validate next to prevent open redirect)
    if not next.startswith("/") or next.startswith("//"):
        next = "/people"
    if get_session(request):
        return RedirectResponse(next, status_code=302)
    csrf = generate_csrf_token()
    success = "Contraseña actualizada correctamente. Inicia sesión con tu nueva contraseña." if reset == "1" else None
    response = _templates.TemplateResponse(
        "login.html",
        {"request": request, "next": next, "csrf_token": csrf, "error": None, "success": success,
         "app_settings": request.state.app_settings if hasattr(request.state, "app_settings") else None},
    )
    response.set_cookie(
        "login_csrf",
        csrf,
        httponly=True,
        samesite="lax",
        max_age=300,  # 5 minutes
    )
    return response


@app.post("/admin/login", include_in_schema=False)
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/people"),
    csrf_token: str = Form(default=""),
):
    ip = _get_ip(request)

    username = username.strip().lower()
    db = SessionLocal()
    try:
        valid = verify_admin_login(username, password, db)
    finally:
        db.close()

    if not valid:
        security_logger.warning("LOGIN_FAIL | ip=%s | user=%s", ip, username)
        csrf = generate_csrf_token()
        response = _templates.TemplateResponse(
            "login.html",
            {"request": request, "next": next, "csrf_token": csrf, "error": "Credenciales incorrectas", "success": None,
             "app_settings": request.state.app_settings if hasattr(request.state, "app_settings") else None},
            status_code=401,
        )
        response.set_cookie("login_csrf", csrf, httponly=True, samesite="lax", max_age=300)
        return response

    security_logger.info("LOGIN_OK | ip=%s | user=%s", ip, username)
    session_token = create_session_token(username)
    csrf_val = generate_csrf_token()

    # Ensure next is a relative path (prevent open redirect)
    if not next.startswith("/") or next.startswith("//"):
        next = "/people"

    response = RedirectResponse(next, status_code=302)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    # Non-HttpOnly CSRF cookie so JS can read it
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_val,
        httponly=False,
        samesite="lax",
        max_age=86400 * 7,
    )
    response.delete_cookie("login_csrf")
    return response


@app.get("/admin/logout", include_in_schema=False)
def admin_logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE_NAME)
    response.delete_cookie(CSRF_COOKIE_NAME)
    return response


# ── Profile photo endpoint (served from portal) ───────────────────────────────
@app.get("/portal/photo", include_in_schema=False)
def portal_photo(request: Request):
    """Serve current user's profile photo."""
    session = get_user_session(request)
    if not session:
        return RedirectResponse("/user/login", status_code=302)
    db = SessionLocal()
    try:
        from app.models.user import User
        user = db.get(User, session["user_id"])
        if user and user.profile_photo_path:
            path = Path(user.profile_photo_path)
            if path.exists():
                media = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                return FileResponse(path, media_type=media)
    finally:
        db.close()
    return RedirectResponse("/static/css/app.css", status_code=302)  # fallback


@app.get("/branding/logo", include_in_schema=False)
def branding_logo():
    """Serve the app logo stored in storage/branding/."""
    from app.db import SessionLocal as SL
    from app.models.app_settings import AppSettings
    db = SL()
    try:
        s = db.get(AppSettings, 1)
        if s and s.logo_path:
            p = Path(s.logo_path)
            if p.exists():
                media = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                return FileResponse(p, media_type=media)
    finally:
        db.close()
    from fastapi.responses import Response as FResponse
    return FResponse(status_code=404)


# ── Application routers ───────────────────────────────────────────────────────
app.include_router(recovery_router)
app.include_router(pages.router)
app.include_router(backups_router)
app.include_router(admin_users_router)
app.include_router(admin_settings_router)
app.include_router(public_forms.router)
app.include_router(user_auth_router)
app.include_router(portal_router)
app.include_router(people.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(payrolls.router, prefix="/api")
