"""Admin route for app-level settings: /admin/settings."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.models.app_settings import AppSettings
from app.security.logging import security_logger
from app.security.rate_limiter import limiter

router = APIRouter(prefix="/admin", tags=["admin-settings"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")

Path("storage/branding").mkdir(parents=True, exist_ok=True)

_ALLOWED_IMG_MAGIC = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG": "png",
}


def _is_valid_image(data: bytes) -> str | None:
    """Return extension if valid image, else None."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"\x89PNG":
        return "png"
    return None


def _get_or_create_settings(db: Session) -> AppSettings:
    s = db.get(AppSettings, 1)
    if not s:
        s = AppSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("/settings", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def admin_settings_page(request: Request, db: Session = Depends(get_db)):
    s = _get_or_create_settings(db)
    return templates.TemplateResponse(
        "admin_settings.html",
        {"request": request, "s": s, "error": None, "success": None},
    )


@router.post("/settings", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def admin_settings_save(
    request: Request,
    app_name: str = Form(...),
    primary_color: str = Form(default="#6366f1"),
    secondary_color: str = Form(default="#3563e9"),
    welcome_text: str = Form(default=""),
    logo: UploadFile = File(default=None),
    db: Session = Depends(get_db),
):
    s = _get_or_create_settings(db)

    s.app_name = app_name.strip() or "People Manager"
    s.primary_color = primary_color.strip() or "#6366f1"
    s.secondary_color = secondary_color.strip() or "#3563e9"
    s.welcome_text = welcome_text.strip() or None

    # Handle logo upload
    if logo and logo.filename:
        max_size = 5 * 1024 * 1024
        data = await logo.read(max_size + 1)
        if len(data) > max_size:
            return templates.TemplateResponse(
                "admin_settings.html",
                {"request": request, "s": s, "error": "El logo no puede superar 5 MB.", "success": None},
                status_code=400,
            )
        ext = _is_valid_image(data)
        if not ext:
            return templates.TemplateResponse(
                "admin_settings.html",
                {"request": request, "s": s, "error": "Solo se admiten imágenes JPG o PNG.", "success": None},
                status_code=400,
            )
        filename = f"logo_{uuid.uuid4().hex}.{ext}"
        dest = Path("storage/branding") / filename
        dest.write_bytes(data)
        # Remove old logo if different
        if s.logo_path and s.logo_path != str(dest):
            old = Path(s.logo_path)
            if old.exists():
                old.unlink(missing_ok=True)
        s.logo_path = str(dest)

    db.commit()
    db.refresh(s)
    security_logger.info("ADMIN_SETTINGS_SAVE | app_name=%s", s.app_name)
    return templates.TemplateResponse(
        "admin_settings.html",
        {"request": request, "s": s, "error": None, "success": "Configuración guardada correctamente."},
    )


@router.post("/settings/remove-logo", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def admin_settings_remove_logo(request: Request, db: Session = Depends(get_db)):
    s = _get_or_create_settings(db)
    if s.logo_path:
        old = Path(s.logo_path)
        if old.exists():
            old.unlink(missing_ok=True)
        s.logo_path = None
        db.commit()
        db.refresh(s)
    return templates.TemplateResponse(
        "admin_settings.html",
        {"request": request, "s": s, "error": None, "success": "Logo eliminado."},
    )
