from pathlib import Path
from uuid import uuid4

from app.config import settings


def ensure_storage() -> Path:
    path = Path(settings.storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_pdf_path(filename: str) -> tuple[str, Path]:
    storage_dir = ensure_storage()
    stored_name = f"{uuid4()}.pdf"
    return stored_name, storage_dir / stored_name


def build_image_path(extension: str) -> tuple[str, Path]:
    """Return (stored_name, destination_path) for an image file.

    Images are stored under storage/photos/ (sibling of the PDFs folder).
    ``extension`` must include the leading dot, e.g. '.jpg'.
    """
    photos_dir = Path(settings.storage_dir).parent / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4()}{extension}"
    return stored_name, photos_dir / stored_name
