from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.models import Document
from app.schemas.document import DocumentOut
from app.security.rate_limiter import limiter
from app.services.document_service import delete_document, save_document
from app.services.person_service import get_person

router = APIRouter(tags=["documents"])


@router.get("/people/{person_id}/documents", response_model=list[DocumentOut])
@limiter.limit(settings.rate_limit_general)
def api_list_documents(person_id: int, request: Request, db: Session = Depends(get_db)):
    person = get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return person.documents


@router.post("/people/{person_id}/documents", response_model=DocumentOut, status_code=201)
@limiter.limit(settings.rate_limit_upload)
def api_upload_document(
    person_id: int,
    request: Request,
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    description: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    person = get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return save_document(db, person, file, category, description)


@router.get("/documents/{document_id}", response_model=DocumentOut)
@limiter.limit(settings.rate_limit_general)
def api_get_document(document_id: int, request: Request, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return document


@router.get("/documents/{document_id}/file")
@limiter.limit(settings.rate_limit_general)
def api_get_document_file(document_id: int, request: Request, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    path = Path(document.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type=document.mime_type, filename=document.original_filename)


@router.delete("/documents/{document_id}", status_code=204)
@limiter.limit(settings.rate_limit_put)
def api_delete_document(document_id: int, request: Request, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    delete_document(db, document)
    return None
