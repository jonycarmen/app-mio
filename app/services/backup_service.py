"""Backup service: create, list, restore and schedule automatic backups."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import threading
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, engine
from app.models.backup import BackupRecord

# ── Paths ─────────────────────────────────────────────────────────────────────
DB_PATH = Path("app.db")
PDFS_DIR = Path(settings.storage_dir)
ENV_FILE = Path(".env")
CONFIG_FILE = Path("storage/backup_config.json")

# ── Auto-backup state ─────────────────────────────────────────────────────────
_stop_event = threading.Event()
_auto_thread: threading.Thread | None = None


# ── Last-destination config (persisted in a small JSON sidecar) ──────────────

def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_destination": ""}


def _save_config(data: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_last_destination() -> str:
    return _load_config().get("last_destination", "")


def set_last_destination(path: str) -> None:
    cfg = _load_config()
    cfg["last_destination"] = path
    _save_config(cfg)


# ── ZIP builder ───────────────────────────────────────────────────────────────

def _build_zip_bytes() -> tuple[str, bytes]:
    """Return (filename, zip_bytes) containing DB + PDFs + .env."""
    now = datetime.now()
    filename = f"backup_{now.strftime('%Y-%m-%d_%H-%M-%S')}.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if DB_PATH.exists():
            zf.write(DB_PATH, "app.db")
        if PDFS_DIR.exists():
            for f in PDFS_DIR.rglob("*"):
                if f.is_file():
                    zf.write(f, str(f.relative_to(PDFS_DIR.parent)))
        if ENV_FILE.exists():
            zf.write(ENV_FILE, ".env")
    return filename, buf.getvalue()


# ── Public API ────────────────────────────────────────────────────────────────

def create_backup(
    destination_path: str, db: Session, backup_type: str = "manual"
) -> BackupRecord:
    """Create a ZIP backup, save it to *destination_path*, and record it in DB."""
    filename, data = _build_zip_bytes()
    dest = Path(destination_path)
    dest.mkdir(parents=True, exist_ok=True)
    full_path = dest / filename
    full_path.write_bytes(data)

    record = BackupRecord(
        filename=filename,
        destination_path=str(dest),
        full_path=str(full_path),
        size_bytes=len(data),
        type=backup_type,
        status="ok",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    set_last_destination(destination_path)
    return record


def create_download_backup(db: Session) -> tuple[str, bytes]:
    """Create a backup ZIP in memory for direct browser download."""
    filename, data = _build_zip_bytes()
    record = BackupRecord(
        filename=filename,
        destination_path="[descarga directa]",
        full_path="",
        size_bytes=len(data),
        type="download",
        status="ok",
    )
    db.add(record)
    db.commit()
    return filename, data


def list_backups(db: Session) -> list[BackupRecord]:
    return (
        db.execute(select(BackupRecord).order_by(BackupRecord.created_at.desc()))
        .scalars()
        .all()
    )


def get_backup(backup_id: int, db: Session) -> BackupRecord | None:
    return db.get(BackupRecord, backup_id)


def delete_backup_record(backup_id: int, db: Session) -> bool:
    record = db.get(BackupRecord, backup_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


# ── Validation ────────────────────────────────────────────────────────────────

def validate_backup_zip_bytes(data: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return "app.db" in zf.namelist()
    except Exception:
        return False


def validate_backup_zip_path(path: str | Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return "app.db" in zf.namelist()
    except Exception:
        return False


# ── Restore helpers ───────────────────────────────────────────────────────────

def _apply_restore(zf: zipfile.ZipFile) -> None:
    """Extract ZIP contents, replace DB and PDFs on disk."""
    names = zf.namelist()
    if "app.db" not in names:
        raise ValueError("ZIP inválido: no contiene app.db")

    with tempfile.TemporaryDirectory() as tmp:
        zf.extractall(tmp)
        tmp_path = Path(tmp)

        # Dispose SQLAlchemy pool to release Windows file locks on app.db
        engine.dispose()

        new_db = tmp_path / "app.db"
        if new_db.exists():
            shutil.copy2(new_db, DB_PATH)

        new_pdfs = tmp_path / "storage" / "pdfs"
        if new_pdfs.exists():
            if PDFS_DIR.exists():
                shutil.rmtree(PDFS_DIR)
            shutil.copytree(new_pdfs, PDFS_DIR)


def restore_backup_bytes(data: bytes) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        _apply_restore(zf)


def restore_backup_from_path(path: str | Path) -> None:
    with zipfile.ZipFile(path) as zf:
        _apply_restore(zf)


# ── Auto-backup background thread ─────────────────────────────────────────────

def _auto_backup_worker() -> None:
    interval_s = settings.backup_auto_interval_hours * 3600
    while not _stop_event.wait(interval_s):
        if not settings.backup_auto_enabled or not settings.backup_auto_path:
            continue
        db = SessionLocal()
        try:
            create_backup(settings.backup_auto_path, db, backup_type="auto")
        except Exception as exc:
            try:
                from app.security.logging import security_logger
                security_logger.error("AUTO_BACKUP_ERROR: %s", exc)
            except Exception:
                pass
        finally:
            db.close()


def start_auto_backup() -> None:
    global _auto_thread, _stop_event
    if not settings.backup_auto_enabled or not settings.backup_auto_path:
        return
    _stop_event.clear()
    _auto_thread = threading.Thread(target=_auto_backup_worker, daemon=True, name="auto-backup")
    _auto_thread.start()


def stop_auto_backup() -> None:
    _stop_event.set()
