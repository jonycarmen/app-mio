import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, Person
from app.security.logging import security_logger
from app.services.storage_service import build_image_path, build_pdf_path

_SAFE_FILENAME_RE = re.compile(r"[^\w\s\-.]")

# Supported file types: (magic_check_fn, mime_type, extension)
# Each entry: (detector callable, mime_type, file_extension)
_SUPPORTED_TYPES: list[tuple] = [
    # PDF
    (lambda b: b[:5] == b"%PDF-", "application/pdf", ".pdf"),
    # JPEG
    (lambda b: b[:3] == b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    # PNG
    (lambda b: b[:8] == b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    # GIF
    (lambda b: b[:6] in (b"GIF87a", b"GIF89a"), "image/gif", ".gif"),
    # WebP  (RIFF....WEBP)
    (lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP", "image/webp", ".webp"),
]


def _sanitize_filename(name: str) -> str:
    """Remove potentially dangerous characters from a filename."""
    name = name.strip()
    name = _SAFE_FILENAME_RE.sub("_", name)
    name = Path(name).name
    if len(name) > 200:
        suffix = Path(name).suffix
        name = name[: 200 - len(suffix)] + suffix
    return name or "document"


def _detect_file_type(content: bytes) -> tuple[str, str] | None:
    """Return (mime_type, extension) for supported types, or None."""
    for detector, mime_type, extension in _SUPPORTED_TYPES:
        if detector(content):
            return mime_type, extension
    return None


def save_document(
    db: Session,
    person: Person,
    upload: UploadFile,
    category: str | None,
    description: str | None,
) -> Document:
    content = upload.file.read()

    # 1. Detect file type from magic bytes
    detected = _detect_file_type(content)
    if detected is None:
        security_logger.warning(
            "FILE_REJECTED | person_id=%s | filename=%s | reason=invalid_magic_bytes",
            person.id,
            upload.filename,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos PDF e imágenes válidas (JPG, PNG, GIF, WebP)",
        )
    mime_type, extension = detected

    # 2. Validate file size
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        security_logger.warning(
            "FILE_REJECTED | person_id=%s | filename=%s | reason=too_large | size=%s",
            person.id,
            upload.filename,
            len(content),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo demasiado grande (máx {settings.max_upload_size_mb} MB)",
        )

    # 3. Validate document count per person
    doc_count = db.query(Document).filter(Document.person_id == person.id).count()
    if doc_count >= settings.max_docs_per_person:
        security_logger.warning(
            "FILE_REJECTED | person_id=%s | reason=doc_limit_exceeded | count=%s",
            person.id,
            doc_count,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Límite de documentos alcanzado (máx {settings.max_docs_per_person})",
        )

    # 4. Sanitize original filename
    original_name = _sanitize_filename(upload.filename or "document")

    # 5. Choose storage path based on type
    if mime_type == "application/pdf":
        stored_name, destination = build_pdf_path(original_name)
    else:
        stored_name, destination = build_image_path(extension)

    destination.write_bytes(content)

    document = Document(
        person_id=person.id,
        original_filename=original_name,
        stored_filename=stored_name,
        file_path=str(destination),
        mime_type=mime_type,
        file_size=len(content),
        category=category,
        description=description,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, document: Document) -> None:
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()
    db.delete(document)
    db.commit()
