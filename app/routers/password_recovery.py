"""Password recovery routes: forgot-password → verify-code → reset-password."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.admin import Admin, VerificationCode
from app.security.auth import (
    RESET_PENDING_COOKIE,
    RESET_VERIFIED_COOKIE,
    VERIFY_ATTEMPTS_COOKIE,
    create_reset_pending_token,
    create_reset_verified_token,
    create_verify_attempts_token,
    generate_csrf_token,
    get_verify_attempts,
    hash_password,
    verify_password,
    verify_reset_pending_token,
    verify_reset_verified_token,
    _get_ip,
)
from app.security.logging import security_logger
from app.security.rate_limiter import limiter
from app.services.email_service import is_email_configured, send_verification_code
from app.services.sms_service import is_sms_configured, send_verification_sms

router = APIRouter(include_in_schema=False)
_templates = Jinja2Templates(directory="app/templates")

MAX_VERIFY_ATTEMPTS = 5
CODE_TTL_MINUTES = 15


# ---------------------------------------------------------------------------
# Step 1 — Forgot password
# ---------------------------------------------------------------------------

@router.get("/admin/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    csrf = generate_csrf_token()
    resp = _templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "csrf_token": csrf,
            "error": None,
            "success": None,
            "sms_available": is_sms_configured(),
            "email_available": is_email_configured(),
        },
    )
    resp.set_cookie("fp_csrf", csrf, httponly=True, samesite="strict", max_age=300)
    return resp


@router.post("/admin/forgot-password", response_class=HTMLResponse)
@limiter.limit("3/hour")
async def forgot_password_submit(
    request: Request,
    channel: str = Form(...),       # 'email' or 'sms'
    contact: str = Form(...),       # email address or phone number
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    ip = _get_ip(request)

    # CSRF check
    if not secrets.compare_digest(csrf_token, request.cookies.get("fp_csrf", "")):
        security_logger.warning("FORGOT_CSRF_FAIL | ip=%s", ip)
        return _forgot_page(request, error="Solicitud inválida.")

    contact = contact.strip()
    if not contact:
        return _forgot_page(request, error="Por favor ingresa un email o teléfono.")

    # Validate channel availability
    if channel == "sms" and not is_sms_configured():
        return _forgot_page(request, error="El envío por SMS no está disponible.")
    if channel == "email" and not is_email_configured():
        return _forgot_page(request, error="El envío por email no está disponible.")

    # Look up admin (don't reveal if found)
    admin: Admin | None = None
    if channel == "email":
        admin = db.query(Admin).filter(Admin.email == contact).first()
    else:
        admin = db.query(Admin).filter(Admin.phone == contact).first()

    security_logger.info(
        "FORGOT_PASSWORD | ip=%s | channel=%s | found=%s", ip, channel, admin is not None
    )

    # Always show the same success message (prevents enumeration)
    success_msg = (
        f"Si existe una cuenta con ese {'email' if channel == 'email' else 'teléfono'}, "
        "recibirás un código en breve."
    )

    if admin is not None:
        # Generate 6-digit code
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        code_hash = hash_password(code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES)

        vc = VerificationCode(
            admin_id=admin.id,
            code_hash=code_hash,
            type=channel,
            expires_at=expires_at,
            used=False,
        )
        db.add(vc)
        db.commit()

        # Send
        sent = False
        if channel == "email":
            sent = send_verification_code(contact, code)
        else:
            sent = send_verification_sms(contact, code)

        if not sent:
            security_logger.error("FORGOT_SEND_FAIL | ip=%s | admin_id=%s", ip, admin.id)

        # Set signed pending cookie
        pending_token = create_reset_pending_token(admin.id)
        resp = _forgot_page(request, success=success_msg)
        resp.set_cookie(RESET_PENDING_COOKIE, pending_token, httponly=True, samesite="strict", max_age=960)
        resp.delete_cookie("fp_csrf")
        return resp

    # Admin not found — same UX, no cookie
    resp = _forgot_page(request, success=success_msg)
    resp.delete_cookie("fp_csrf")
    return resp


def _forgot_page(request: Request, error: str | None = None, success: str | None = None):
    csrf = generate_csrf_token()
    resp = _templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "csrf_token": csrf,
            "error": error,
            "success": success,
            "sms_available": is_sms_configured(),
            "email_available": is_email_configured(),
        },
    )
    resp.set_cookie("fp_csrf", csrf, httponly=True, samesite="strict", max_age=300)
    return resp


# ---------------------------------------------------------------------------
# Step 2 — Verify code
# ---------------------------------------------------------------------------

@router.get("/admin/verify-code", response_class=HTMLResponse)
def verify_code_page(request: Request):
    # Check that step 1 was completed
    pending_cookie = request.cookies.get(RESET_PENDING_COOKIE)
    if not pending_cookie or not verify_reset_pending_token(pending_cookie):
        return RedirectResponse("/admin/forgot-password", status_code=302)

    csrf = generate_csrf_token()
    resp = _templates.TemplateResponse(
        "verify_code.html",
        {"request": request, "csrf_token": csrf, "error": None},
    )
    resp.set_cookie("vc_csrf", csrf, httponly=True, samesite="strict", max_age=300)
    return resp


@router.post("/admin/verify-code", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def verify_code_submit(
    request: Request,
    code: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    ip = _get_ip(request)

    # Check step-1 cookie
    pending_cookie = request.cookies.get(RESET_PENDING_COOKIE)
    payload = verify_reset_pending_token(pending_cookie or "")
    if not payload:
        return RedirectResponse("/admin/forgot-password", status_code=302)

    admin_id: int = payload["admin_id"]

    # CSRF check
    if not secrets.compare_digest(csrf_token, request.cookies.get("vc_csrf", "")):
        security_logger.warning("VERIFY_CSRF_FAIL | ip=%s", ip)
        return _verify_page(request, error="Solicitud inválida.")

    # Rate-limit attempts per session
    attempts = get_verify_attempts(request, admin_id)
    if attempts >= MAX_VERIFY_ATTEMPTS:
        security_logger.warning("VERIFY_MAX_ATTEMPTS | ip=%s | admin_id=%s", ip, admin_id)
        return _verify_page(request, error="Demasiados intentos. Solicita un nuevo código.")

    code = code.strip()
    now = datetime.now(timezone.utc)

    # Find latest valid code for this admin
    vc: VerificationCode | None = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.admin_id == admin_id,
            VerificationCode.used == False,  # noqa: E712
            VerificationCode.expires_at > now,
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )

    code_valid = False
    if vc:
        code_valid = verify_password(code, vc.code_hash)

    if not code_valid:
        new_attempts = attempts + 1
        security_logger.warning(
            "VERIFY_FAIL | ip=%s | admin_id=%s | attempt=%d", ip, admin_id, new_attempts
        )
        remaining = MAX_VERIFY_ATTEMPTS - new_attempts
        resp = _verify_page(
            request,
            error=f"Código incorrecto o expirado. Intentos restantes: {remaining}.",
        )
        attempts_token = create_verify_attempts_token(admin_id, new_attempts)
        resp.set_cookie(VERIFY_ATTEMPTS_COOKIE, attempts_token, httponly=True, samesite="strict", max_age=960)
        return resp

    # Code is valid — mark as used
    vc.used = True
    db.commit()
    security_logger.info("VERIFY_OK | ip=%s | admin_id=%s", ip, admin_id)

    # Set verified cookie and clear pending/attempts
    verified_token = create_reset_verified_token(admin_id)
    resp = RedirectResponse("/admin/reset-password", status_code=302)
    resp.set_cookie(RESET_VERIFIED_COOKIE, verified_token, httponly=True, samesite="strict", max_age=660)
    resp.delete_cookie(RESET_PENDING_COOKIE)
    resp.delete_cookie(VERIFY_ATTEMPTS_COOKIE)
    resp.delete_cookie("vc_csrf")
    return resp


def _verify_page(request: Request, error: str | None = None):
    csrf = generate_csrf_token()
    resp = _templates.TemplateResponse(
        "verify_code.html",
        {"request": request, "csrf_token": csrf, "error": error},
    )
    resp.set_cookie("vc_csrf", csrf, httponly=True, samesite="strict", max_age=300)
    return resp


# ---------------------------------------------------------------------------
# Step 3 — Reset password
# ---------------------------------------------------------------------------

@router.get("/admin/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request):
    verified_cookie = request.cookies.get(RESET_VERIFIED_COOKIE)
    if not verified_cookie or not verify_reset_verified_token(verified_cookie):
        return RedirectResponse("/admin/forgot-password", status_code=302)

    csrf = generate_csrf_token()
    resp = _templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "csrf_token": csrf, "error": None},
    )
    resp.set_cookie("rp_csrf", csrf, httponly=True, samesite="strict", max_age=300)
    return resp


@router.post("/admin/reset-password", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def reset_password_submit(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    ip = _get_ip(request)

    # Check step-2 cookie
    verified_cookie = request.cookies.get(RESET_VERIFIED_COOKIE)
    payload = verify_reset_verified_token(verified_cookie or "")
    if not payload:
        return RedirectResponse("/admin/forgot-password", status_code=302)

    admin_id: int = payload["admin_id"]

    # CSRF check
    if not secrets.compare_digest(csrf_token, request.cookies.get("rp_csrf", "")):
        security_logger.warning("RESET_CSRF_FAIL | ip=%s", ip)
        return _reset_page(request, error="Solicitud inválida.")

    if new_password != confirm_password:
        return _reset_page(request, error="Las contraseñas no coinciden.")

    if len(new_password) < 8:
        return _reset_page(request, error="La contraseña debe tener al menos 8 caracteres.")

    admin: Admin | None = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        security_logger.error("RESET_ADMIN_NOT_FOUND | ip=%s | admin_id=%s", ip, admin_id)
        return RedirectResponse("/admin/forgot-password", status_code=302)

    admin.password_hash = hash_password(new_password)
    db.commit()
    security_logger.info("PASSWORD_RESET_OK | ip=%s | admin_id=%s | username=%s", ip, admin_id, admin.username)

    resp = RedirectResponse("/admin/login?reset=1", status_code=302)
    resp.delete_cookie(RESET_VERIFIED_COOKIE)
    resp.delete_cookie("rp_csrf")
    return resp


def _reset_page(request: Request, error: str | None = None):
    csrf = generate_csrf_token()
    resp = _templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "csrf_token": csrf, "error": error},
    )
    resp.set_cookie("rp_csrf", csrf, httponly=True, samesite="strict", max_age=300)
    return resp
