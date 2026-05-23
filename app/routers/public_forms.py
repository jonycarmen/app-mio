from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.models import Document
from app.schemas.document import DocumentOut
from app.schemas.person import PublicPersonOut, PublicPersonUpdate
from app.security.logging import security_logger
from app.security.rate_limiter import limiter
from app.services.document_service import save_document
from app.services.person_service import get_person_by_token, update_public_person

router = APIRouter(tags=["public-form"])
templates = Jinja2Templates(directory="app/templates")


def _get_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_person_or_404(db: Session, token: str, request: Request):
    person = get_person_by_token(db, token)
    ip = _get_ip(request)
    if not person:
        security_logger.warning("TOKEN_INVALID | ip=%s | token=%s", ip, token[:8] + "…")
        raise HTTPException(status_code=404, detail="Enlace no válido")
    # Check token expiry
    if person.expires_at and datetime.now(timezone.utc) > person.expires_at:
        security_logger.warning(
            "TOKEN_EXPIRED | ip=%s | person_id=%s | token=%s",
            ip, person.id, token[:8] + "…",
        )
        raise HTTPException(status_code=410, detail="Este enlace ha expirado")
    security_logger.info(
        "TOKEN_ACCESS | ip=%s | person_id=%s | path=%s", ip, person.id, request.url.path
    )
    return person


@router.get("/form/{token}", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def public_form(token: str, request: Request, db: Session = Depends(get_db)):
    person = _get_person_or_404(db, token, request)
    return templates.TemplateResponse(
        "public_form.html",
        {
            "request": request,
            "person": person,
            "token": token,
            "public_view": True,
        },
    )


@router.put("/form/{token}", response_model=PublicPersonOut)
@limiter.limit(settings.rate_limit_put)
def update_public_form(
    token: str,
    request: Request,
    payload: PublicPersonUpdate,
    db: Session = Depends(get_db),
):
    person = _get_person_or_404(db, token, request)
    try:
        return update_public_person(db, person, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="DNI o pasaporte duplicado")


@router.post(
    "/form/{token}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_upload)
def upload_public_document(
    token: str,
    request: Request,
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    description: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    person = _get_person_or_404(db, token, request)
    return save_document(db, person, file, category, description)


@router.get("/form/{token}/documents", response_model=list[DocumentOut])
@limiter.limit(settings.rate_limit_general)
def list_public_documents(token: str, request: Request, db: Session = Depends(get_db)):
    person = _get_person_or_404(db, token, request)
    return person.documents


@router.get("/form/{token}/documents/{doc_id}/file")
@limiter.limit(settings.rate_limit_general)
def get_public_document_file(token: str, doc_id: int, request: Request, db: Session = Depends(get_db)):
    person = _get_person_or_404(db, token, request)
    document = db.get(Document, doc_id)
    if not document or document.person_id != person.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    path = Path(document.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type=document.mime_type, filename=document.original_filename)
