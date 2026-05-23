"""Admin routes for user management and invitations: /admin/users, /admin/invitations."""
import secrets
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.models.invitation import Invitation
from app.models.user import User
from app.security.logging import security_logger
from app.security.rate_limiter import limiter

router = APIRouter(prefix="/admin", tags=["admin-users"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")

# Predefined tag colors
PRESET_COLORS = [
    {"hex": "#ef4444", "name": "Rojo (Descartado)"},
    {"hex": "#22c55e", "name": "Verde (Activo)"},
    {"hex": "#eab308", "name": "Amarillo (Pendiente)"},
    {"hex": "#3b82f6", "name": "Azul (VIP)"},
    {"hex": "#6b7280", "name": "Gris (Inactivo)"},
    {"hex": "#a855f7", "name": "Morado (Prioritario)"},
    {"hex": "#f97316", "name": "Naranja"},
    {"hex": "#06b6d4", "name": "Cyan"},
]


# ---------------------------------------------------------------------------
# Users list
# ---------------------------------------------------------------------------

@router.get("/users", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def admin_users_list(
    request: Request,
    tag: str = "",
    color: str = "",
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if tag:
        q = q.filter(User.admin_tag == tag)
    if color:
        q = q.filter(User.admin_color == color)
    users = q.order_by(User.created_at.desc()).all()

    # Compute tag counts for sidebar (across all users, ignoring filters)
    all_users = db.query(User).all()
    tag_counts: Counter = Counter()
    color_counts: Counter = Counter()
    for u in all_users:
        if u.admin_tag:
            tag_counts[u.admin_tag] += 1
        if u.admin_color:
            color_counts[u.admin_color] += 1

    all_tags = sorted(tag_counts.keys())
    all_colors = sorted(color_counts.keys())

    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "users": users,
            "tag_counts": dict(tag_counts),
            "color_counts": dict(color_counts),
            "all_tags": all_tags,
            "all_colors": all_colors,
            "filter_tag": tag,
            "filter_color": color,
            "preset_colors": PRESET_COLORS,
        },
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def admin_user_detail(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        return RedirectResponse("/admin/users", status_code=302)
    person = user.person
    return templates.TemplateResponse(
        "admin_user_detail.html",
        {
            "request": request,
            "user": user,
            "person": person,
            "banks": person.bank_accounts if person else [],
            "wallets": person.wallet_addresses if person else [],
            "documents": person.documents if person else [],
            "payrolls": sorted(person.payroll_entries, key=lambda p: p.effective_date, reverse=True) if person else [],
            "preset_colors": PRESET_COLORS,
            "error": None,
            "success": None,
        },
    )


@router.post("/users/{user_id}", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def admin_user_update(
    user_id: int,
    request: Request,
    display_name: str = Form(...),
    email: str = Form(default=""),
    phone: str = Form(default=""),
    admin_tag: str = Form(default=""),
    admin_color: str = Form(default=""),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        return RedirectResponse("/admin/users", status_code=302)

    email = email.strip().lower() or None
    phone = phone.strip() or None
    display_name = display_name.strip()

    if email:
        existing = db.query(User).filter(User.email == email, User.id != user_id).first()
        if existing:
            return _detail_resp(request, user, db, error="Ese email ya está en uso.")
    if phone:
        existing = db.query(User).filter(User.phone == phone, User.id != user_id).first()
        if existing:
            return _detail_resp(request, user, db, error="Ese teléfono ya está en uso.")

    user.display_name = display_name
    user.email = email
    user.phone = phone
    user.admin_tag = admin_tag.strip() or None
    user.admin_color = admin_color.strip() or None

    if user.person:
        user.person.full_name = display_name
    db.commit()
    db.refresh(user)

    security_logger.info("ADMIN_USER_UPDATE | user_id=%s", user_id)
    return _detail_resp(request, user, db, success="Usuario actualizado correctamente.")


@router.post("/users/{user_id}/toggle", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def admin_user_toggle(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        return RedirectResponse("/admin/users", status_code=302)
    user.is_active = not user.is_active
    db.commit()
    action = "activado" if user.is_active else "desactivado"
    security_logger.info("ADMIN_USER_TOGGLE | user_id=%s | active=%s", user_id, user.is_active)
    return _detail_resp(request, user, db, success=f"Usuario {action} correctamente.")


@router.post("/users/{user_id}/delete", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def admin_user_delete(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        return RedirectResponse("/admin/users", status_code=302)
    # Delete associated person and all cascaded data (bank_accounts, wallets, documents, payrolls)
    if user.person:
        from app.models.document import Document
        import os
        docs = user.person.documents
        for doc in docs:
            try:
                if os.path.exists(doc.file_path):
                    os.remove(doc.file_path)
            except Exception:
                pass
        db.delete(user.person)
    display = user.display_name
    db.delete(user)
    db.commit()
    security_logger.info("ADMIN_USER_DELETE | user_id=%s | name=%s", user_id, display)
    return RedirectResponse("/admin/users", status_code=302)


def _detail_resp(request, user, db, error=None, success=None):
    person = user.person
    return templates.TemplateResponse(
        "admin_user_detail.html",
        {
            "request": request,
            "user": user,
            "person": person,
            "banks": person.bank_accounts if person else [],
            "wallets": person.wallet_addresses if person else [],
            "documents": person.documents if person else [],
            "payrolls": sorted(person.payroll_entries, key=lambda p: p.effective_date, reverse=True) if person else [],
            "preset_colors": PRESET_COLORS,
            "error": error,
            "success": success,
        },
    )


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

def _invitations_list_response(request, db, error=None, success=None, new_token=None, detail_id=None):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Auto-expire pending invitations
    pending = db.query(Invitation).filter(
        Invitation.status == "pending", Invitation.expires_at < now
    ).all()
    for inv in pending:
        inv.status = "expired"
    if pending:
        db.commit()

    invitations = db.query(Invitation).order_by(Invitation.created_at.desc()).all()

    inv_detail = None
    if detail_id:
        inv_detail = db.get(Invitation, detail_id)

    return templates.TemplateResponse(
        "admin_invitations.html",
        {
            "request": request,
            "invitations": invitations,
            "now": now,
            "error": error,
            "success": success,
            "new_token": new_token,
            "inv_detail": inv_detail,
        },
    )


@router.get("/invitations", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def admin_invitations(request: Request, detail_id: int | None = None, db: Session = Depends(get_db)):
    return _invitations_list_response(request, db, detail_id=detail_id)


@router.post("/invitations", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def admin_create_invitation(
    request: Request,
    inv_type: str = Form(default="personal"),
    email: str = Form(default=""),
    expires_hours: int = Form(default=72),
    label: str = Form(default=""),
    max_uses: str = Form(default=""),
    db: Session = Depends(get_db),
):
    inv_type = inv_type if inv_type in ("personal", "group") else "personal"
    email = email.strip().lower() or None
    expires_hours = max(1, min(expires_hours, 720))  # 1h .. 30 days
    label_val = label.strip() or None
    MAX_GROUP_USES = 200
    max_uses_val: int | None = None
    if inv_type == "group":
        if max_uses.strip():
            try:
                max_uses_val = min(max(1, int(max_uses.strip())), MAX_GROUP_USES)
            except ValueError:
                return _invitations_list_response(request, db, error="El máximo de usos debe ser un número entero.")
        else:
            max_uses_val = MAX_GROUP_USES  # blank = no limit → cap at 200

    # Use naive UTC for consistency with SQLite DateTime storage
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at = now_utc + timedelta(hours=expires_hours)
    # Short mobile-friendly token (8 chars, alphanumeric, easy to type/share)
    token = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))

    inv = Invitation(
        token=token,
        email=email if inv_type == "personal" else None,
        expires_at=expires_at,
        status="pending",
        type=inv_type,
        label=label_val,
        max_uses=max_uses_val,
        current_uses=0,
    )
    db.add(inv)
    db.commit()

    security_logger.info(
        "ADMIN_INV_CREATE | token=%s | type=%s | label=%s | max_uses=%s",
        token[:8], inv_type, label_val, max_uses_val,
    )

    return _invitations_list_response(
        request, db,
        success=f"Invitación {'grupal' if inv_type == 'group' else 'personal'} creada.",
        new_token=token,
    )


@router.post("/invitations/{inv_id}/delete", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def admin_delete_invitation(inv_id: int, request: Request, db: Session = Depends(get_db)):
    inv = db.get(Invitation, inv_id)
    if inv:
        db.delete(inv)
        db.commit()
        security_logger.info("ADMIN_INV_DELETE | id=%s", inv_id)
    return RedirectResponse("/admin/invitations", status_code=302)
