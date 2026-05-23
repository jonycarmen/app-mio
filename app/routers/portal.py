"""Portal personal del usuario: /portal/*"""
import io
import struct
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.models.bank_account import BankAccount
from app.models.document import Document
from app.models.user import User
from app.models.wallet_address import WalletAddress
from app.security.logging import security_logger
from app.security.rate_limiter import limiter
from app.security.user_auth import get_ip, get_user_session
from app.services.document_service import save_document

router = APIRouter(prefix="/portal", tags=["portal"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")

Path("storage/profiles").mkdir(parents=True, exist_ok=True)


def _get_current_user(request: Request, db: Session) -> User | None:
    session = get_user_session(request)
    if not session:
        return None
    return db.get(User, session["user_id"])


def _require_user(request: Request, db: Session) -> User:
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        raise Exception("not_authenticated")
    return user


def _portal_ctx(request: Request, user: User, **extra) -> dict:
    return {"request": request, "user": user, **extra}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def portal_dashboard(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login?next=/portal/", status_code=302)

    person = user.person
    doc_count = len(person.documents) if person else 0
    bank_count = len(person.bank_accounts) if person else 0
    wallet_count = len(person.wallet_addresses) if person else 0
    latest_payroll = None
    if person and person.payroll_entries:
        latest_payroll = sorted(person.payroll_entries, key=lambda p: p.effective_date, reverse=True)[0]

    return templates.TemplateResponse(
        "portal_dashboard.html",
        _portal_ctx(request, user,
                    person=person,
                    doc_count=doc_count,
                    bank_count=bank_count,
                    wallet_count=wallet_count,
                    latest_payroll=latest_payroll),
    )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/profile", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def portal_profile(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login?next=/portal/profile", status_code=302)
    return templates.TemplateResponse(
        "portal_profile.html",
        _portal_ctx(request, user, person=user.person, error=None, success=None),
    )


@router.post("/profile", response_class=HTMLResponse)
@limiter.limit("15/minute")
async def portal_profile_save(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(default=""),
    phone: str = Form(default=""),
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login", status_code=302)

    email = email.strip().lower() or None
    phone = phone.strip() or None
    display_name = display_name.strip()

    if len(display_name) < 2:
        return templates.TemplateResponse(
            "portal_profile.html",
            _portal_ctx(request, user, person=user.person, error="El nombre debe tener al menos 2 caracteres.", success=None),
            status_code=400,
        )

    # Uniqueness check (exclude self)
    if email:
        existing = db.query(User).filter(User.email == email, User.id != user.id).first()
        if existing:
            return templates.TemplateResponse(
                "portal_profile.html",
                _portal_ctx(request, user, person=user.person, error="Ese email ya está en uso.", success=None),
                status_code=400,
            )
    if phone:
        existing = db.query(User).filter(User.phone == phone, User.id != user.id).first()
        if existing:
            return templates.TemplateResponse(
                "portal_profile.html",
                _portal_ctx(request, user, person=user.person, error="Ese teléfono ya está en uso.", success=None),
                status_code=400,
            )

    user.display_name = display_name
    user.email = email
    user.phone = phone
    if user.person:
        user.person.full_name = display_name
    db.commit()
    db.refresh(user)

    return templates.TemplateResponse(
        "portal_profile.html",
        _portal_ctx(request, user, person=user.person, error=None, success="Perfil actualizado correctamente."),
    )


# ---------------------------------------------------------------------------
# Identity (DNI / Passport)
# ---------------------------------------------------------------------------

@router.post("/identity", response_class=HTMLResponse)
@limiter.limit("15/minute")
async def portal_identity_save(
    request: Request,
    dni: str = Form(default=""),
    passport: str = Form(default=""),
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login", status_code=302)
    if not user.person:
        return RedirectResponse("/portal/profile", status_code=302)

    person = user.person
    dni = dni.strip() or None
    passport = passport.strip() or None

    # Check uniqueness
    from app.models.person import Person
    if dni:
        existing = db.query(Person).filter(Person.dni == dni, Person.id != person.id).first()
        if existing:
            return templates.TemplateResponse(
                "portal_profile.html",
                _portal_ctx(request, user, person=person, error="Ese DNI ya está registrado.", success=None),
                status_code=400,
            )
    if passport:
        existing = db.query(Person).filter(Person.passport == passport, Person.id != person.id).first()
        if existing:
            return templates.TemplateResponse(
                "portal_profile.html",
                _portal_ctx(request, user, person=person, error="Ese pasaporte ya está registrado.", success=None),
                status_code=400,
            )

    person.dni = dni
    person.passport = passport
    db.commit()
    db.refresh(person)

    return templates.TemplateResponse(
        "portal_profile.html",
        _portal_ctx(request, user, person=person, error=None, success="DNI y pasaporte actualizados correctamente."),
    )


# ---------------------------------------------------------------------------
# Customization
# ---------------------------------------------------------------------------

@router.get("/customize", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def portal_customize(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login?next=/portal/customize", status_code=302)
    return templates.TemplateResponse(
        "portal_customize.html",
        _portal_ctx(request, user, error=None, success=None),
    )


@router.post("/customize", response_class=HTMLResponse)
@limiter.limit("15/minute")
async def portal_customize_save(
    request: Request,
    theme_color: str = Form(...),
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login", status_code=302)

    color = theme_color.strip()
    if not color.startswith("#") or len(color) not in (4, 7):
        color = "#3563e9"

    user.theme_color = color
    db.commit()
    db.refresh(user)

    return templates.TemplateResponse(
        "portal_customize.html",
        _portal_ctx(request, user, error=None, success="Color guardado correctamente."),
    )


def _is_valid_image(data: bytes) -> bool:
    """Check magic bytes for JPEG or PNG."""
    if data[:3] == b"\xff\xd8\xff":
        return True  # JPEG
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True  # PNG
    return False


@router.post("/customize/photo", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def portal_customize_photo(
    request: Request,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login", status_code=302)

    max_size = 5 * 1024 * 1024  # 5 MB
    data = await photo.read(max_size + 1)
    if len(data) > max_size:
        return templates.TemplateResponse(
            "portal_customize.html",
            _portal_ctx(request, user, error="La imagen no puede superar 5 MB.", success=None),
            status_code=400,
        )
    if not _is_valid_image(data):
        return templates.TemplateResponse(
            "portal_customize.html",
            _portal_ctx(request, user, error="Solo se admiten imágenes JPG o PNG.", success=None),
            status_code=400,
        )

    ext = "jpg" if data[:3] == b"\xff\xd8\xff" else "png"
    filename = f"{uuid.uuid4().hex}.{ext}"
    dest = Path("storage/profiles") / filename
    dest.write_bytes(data)

    # Remove old photo
    if user.profile_photo_path:
        old = Path(user.profile_photo_path)
        if old.exists():
            old.unlink(missing_ok=True)

    user.profile_photo_path = str(dest)
    db.commit()
    db.refresh(user)

    security_logger.info("USER_PHOTO_UPLOAD | user_id=%s | file=%s", user.id, filename)
    return templates.TemplateResponse(
        "portal_customize.html",
        _portal_ctx(request, user, error=None, success="Foto de perfil actualizada."),
    )


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@router.get("/documents", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def portal_documents(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login?next=/portal/documents", status_code=302)
    docs = user.person.documents if user.person else []
    return templates.TemplateResponse(
        "portal_documents.html",
        _portal_ctx(request, user, documents=docs, error=None, success=None),
    )


@router.post("/documents", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_upload)
async def portal_documents_upload(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form(default=None),
    description: str = Form(default=None),
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login", status_code=302)

    if not user.person:
        return RedirectResponse("/portal/documents", status_code=302)

    try:
        save_document(db, user.person, file, category or None, description or None)
        db.refresh(user.person)
        docs = user.person.documents
        return templates.TemplateResponse(
            "portal_documents.html",
            _portal_ctx(request, user, documents=docs, error=None, success="Documento subido correctamente."),
        )
    except Exception as exc:
        docs = user.person.documents if user.person else []
        return templates.TemplateResponse(
            "portal_documents.html",
            _portal_ctx(request, user, documents=docs, error=str(exc), success=None),
            status_code=400,
        )


# ---------------------------------------------------------------------------
# Accounts (bank + wallets)
# ---------------------------------------------------------------------------

@router.get("/accounts", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def portal_accounts(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login?next=/portal/accounts", status_code=302)
    person = user.person
    banks = person.bank_accounts if person else []
    wallets = person.wallet_addresses if person else []
    return templates.TemplateResponse(
        "portal_accounts.html",
        _portal_ctx(request, user, person=person, banks=banks, wallets=wallets, error=None, success=None),
    )


@router.post("/accounts", response_class=HTMLResponse)
@limiter.limit("15/minute")
async def portal_accounts_save(
    request: Request,
    bank_name: str = Form(default=""),
    iban: str = Form(default=""),
    account_number: str = Form(default=""),
    bank_notes: str = Form(default=""),
    wallet_network: str = Form(default=""),
    wallet_address: str = Form(default=""),
    wallet_label: str = Form(default=""),
    wallet_notes: str = Form(default=""),
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login", status_code=302)
    if not user.person:
        return RedirectResponse("/portal/accounts", status_code=302)

    person = user.person

    if bank_name.strip() or iban.strip() or account_number.strip():
        ba = BankAccount(
            person_id=person.id,
            bank_name=bank_name.strip() or None,
            iban=iban.strip() or None,
            account_number=account_number.strip() or None,
            notes=bank_notes.strip() or None,
        )
        db.add(ba)

    if wallet_network.strip() or wallet_address.strip():
        wa = WalletAddress(
            person_id=person.id,
            network=wallet_network.strip() or None,
            address=wallet_address.strip() or "",
            label=wallet_label.strip() or None,
            notes=wallet_notes.strip() or None,
        )
        db.add(wa)

    db.commit()
    db.refresh(person)

    return templates.TemplateResponse(
        "portal_accounts.html",
        _portal_ctx(request, user, person=person,
                    banks=person.bank_accounts,
                    wallets=person.wallet_addresses,
                    error=None, success="Cuenta añadida correctamente."),
    )


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------

@router.get("/payroll", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def portal_payroll(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    if not user or not user.is_active:
        return RedirectResponse("/user/login?next=/portal/payroll", status_code=302)
    person = user.person
    payrolls = []
    if person:
        payrolls = sorted(person.payroll_entries, key=lambda p: p.effective_date, reverse=True)
    return templates.TemplateResponse(
        "portal_payroll.html",
        _portal_ctx(request, user, person=person, payrolls=payrolls),
    )
