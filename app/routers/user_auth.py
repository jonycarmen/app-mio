"""Routes: /register/{token}, /user/login, /user/logout."""
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.models.invitation import Invitation
from app.models.person import Person
from app.models.user import User
from app.security.auth import generate_csrf_token
from app.security.logging import security_logger
from app.security.rate_limiter import limiter
from app.security.user_auth import (
    USER_SESSION_COOKIE_NAME,
    USER_SESSION_MAX_AGE,
    create_user_session_token,
    get_ip,
    get_user_session,
)

router = APIRouter(tags=["user-auth"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


# Short redirect for easy access
@router.get("/login", include_in_schema=False)
@router.get("/acceso", include_in_schema=False)
def user_login_short_redirect(request: Request):
    return RedirectResponse("/user/login", status_code=302)


# Short invitation link redirect: /i/{token} → /register/{token}
@router.get("/i/{token}", include_in_schema=False)
async def short_invite_redirect(token: str):
    return RedirectResponse(f"/register/{token}", status_code=302)


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def _validate_invitation(invitation, db):
    """Return error string if invitation is not usable, else None."""
    if not invitation:
        return "Enlace de invitación no válido."
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now > invitation.expires_at:
        if invitation.status == "pending":
            invitation.status = "expired"
            db.commit()
        return "Este enlace de invitación ha expirado."
    if invitation.status != "pending":
        return "Esta invitación ya fue utilizada o ha expirado."
    if invitation.type == "group" and invitation.max_uses is not None:
        if invitation.current_uses >= invitation.max_uses:
            return "Este enlace de invitación grupal ha alcanzado su límite de usos."
    return None


@router.get("/register/{token}", response_class=HTMLResponse)
@limiter.limit("20/minute")
def register_page(token: str, request: Request, db: Session = Depends(get_db)):
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    error = _validate_invitation(invitation, db)

    csrf = generate_csrf_token()
    resp = templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "token": token,
            "invitation": invitation,
            "csrf_token": csrf,
            "error": error,
        },
    )
    resp.set_cookie("reg_csrf", csrf, httponly=True, samesite="strict", max_age=600)
    return resp


@router.post("/register/{token}", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def register_submit(
    token: str,
    request: Request,
    display_name: str = Form(...),
    email: str = Form(default=""),
    phone: str = Form(default=""),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    ip = get_ip(request)
    csrf_cookie = request.cookies.get("reg_csrf", "")
    if not secrets.compare_digest(csrf_token, csrf_cookie):
        security_logger.warning("REG_CSRF_FAIL | ip=%s", ip)
        inv_csrf = db.query(Invitation).filter(Invitation.token == token).first()
        return _reg_error(request, token, inv_csrf, "Solicitud inválida. Por favor recarga la página.", {})

    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    err = _validate_invitation(invitation, db)
    if err:
        return _reg_error(request, token, invitation, err, {})

    email = email.strip().lower() or None
    phone = phone.strip() or None
    if not email and not phone:
        return _reg_error(request, token, invitation, "Debes ingresar email o teléfono.", {})

    display_name = display_name.strip()
    if len(display_name) < 2:
        return _reg_error(request, token, invitation, "El nombre debe tener al menos 2 caracteres.", {})
    if len(password) < 8:
        return _reg_error(request, token, invitation, "La contraseña debe tener al menos 8 caracteres.", {})

    # Uniqueness checks
    if email and db.query(User).filter(User.email == email).first():
        return _reg_error(request, token, invitation, "Ese email ya está registrado.", {})
    if phone and db.query(User).filter(User.phone == phone).first():
        return _reg_error(request, token, invitation, "Ese teléfono ya está registrado.", {})

    # Create Person + User
    person = Person(full_name=display_name)
    db.add(person)
    db.flush()

    user = User(
        person_id=person.id,
        email=email,
        phone=phone,
        password_hash=_hash_password(password),
        display_name=display_name,
        theme_color="#3563e9",
    )
    db.add(user)
    db.flush()

    # Always link the user to the invitation used
    user.invitation_id = invitation.id

    if invitation.type == "group":
        invitation.current_uses += 1
        # Mark as used only when the max limit has been reached
        if invitation.max_uses is not None and invitation.current_uses >= invitation.max_uses:
            invitation.status = "used"
    else:
        # Personal invitation: single use
        invitation.status = "used"
        invitation.used_by_user_id = user.id

    db.commit()

    security_logger.info("USER_REGISTER | ip=%s | user_id=%s | email=%s", ip, user.id, email)

    # Auto-login
    session_token = create_user_session_token(user.id)
    response = RedirectResponse("/portal/", status_code=302)
    response.set_cookie(
        USER_SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="strict",
        max_age=USER_SESSION_MAX_AGE,
    )
    response.delete_cookie("reg_csrf")
    return response


def _reg_error(request, token, invitation, msg, _extra):
    csrf = generate_csrf_token()
    resp = templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "token": token,
            "invitation": invitation,
            "csrf_token": csrf,
            "error": msg,
        },
        status_code=400,
    )
    resp.set_cookie("reg_csrf", csrf, httponly=True, samesite="strict", max_age=600)
    return resp


# ---------------------------------------------------------------------------
# User Login / Logout
# ---------------------------------------------------------------------------

@router.get("/user/login", response_class=HTMLResponse)
@limiter.limit("30/minute")
def user_login_page(request: Request, next: str = "/portal/"):
    if not next.startswith("/") or next.startswith("//"):
        next = "/portal/"
    if get_user_session(request):
        return RedirectResponse(next, status_code=302)
    csrf = generate_csrf_token()
    resp = templates.TemplateResponse(
        "user_login.html",
        {"request": request, "next": next, "csrf_token": csrf, "error": None},
    )
    resp.set_cookie("ulogin_csrf", csrf, httponly=True, samesite="strict", max_age=300)
    return resp


@router.post("/user/login", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def user_login_submit(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/portal/"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    ip = get_ip(request)
    csrf_cookie = request.cookies.get("ulogin_csrf", "")
    if not secrets.compare_digest(csrf_token, csrf_cookie):
        security_logger.warning("USER_LOGIN_CSRF | ip=%s", ip)
        return _login_error(request, next, "Solicitud inválida.")

    identifier = identifier.strip().lower()
    user = (
        db.query(User).filter(User.email == identifier).first()
        or db.query(User).filter(User.phone == identifier).first()
    )

    if not user or not _verify_password(password, user.password_hash):
        security_logger.warning("USER_LOGIN_FAIL | ip=%s | id=%s", ip, identifier)
        return _login_error(request, next, "Credenciales incorrectas.")

    if not user.is_active:
        security_logger.warning("USER_LOGIN_DISABLED | ip=%s | user_id=%s", ip, user.id)
        return _login_error(request, next, "Cuenta desactivada. Contacta al administrador.")

    security_logger.info("USER_LOGIN_OK | ip=%s | user_id=%s", ip, user.id)
    if not next.startswith("/") or next.startswith("//"):
        next = "/portal/"

    session_token = create_user_session_token(user.id)
    response = RedirectResponse(next, status_code=302)
    response.set_cookie(
        USER_SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="strict",
        max_age=USER_SESSION_MAX_AGE,
    )
    response.delete_cookie("ulogin_csrf")
    return response


def _login_error(request, next_url, msg):
    csrf = generate_csrf_token()
    resp = templates.TemplateResponse(
        "user_login.html",
        {"request": request, "next": next_url, "csrf_token": csrf, "error": msg},
        status_code=401,
    )
    resp.set_cookie("ulogin_csrf", csrf, httponly=True, samesite="strict", max_age=300)
    return resp


@router.get("/user/logout")
def user_logout():
    response = RedirectResponse("/user/login", status_code=302)
    response.delete_cookie(USER_SESSION_COOKIE_NAME)
    return response
