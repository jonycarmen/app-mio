import io

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.security.rate_limiter import limiter
from app.services import backup_service

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


# ── Page ──────────────────────────────────────────────────────────────────────

@router.get("/admin/backups", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def backups_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "backups.html",
        {
            "request": request,
            "backups": backup_service.list_backups(db),
            "last_destination": backup_service.get_last_destination(),
            "auto_enabled": settings.backup_auto_enabled,
            "auto_path": settings.backup_auto_path,
            "auto_interval": settings.backup_auto_interval_hours,
        },
    )


# ── Create backup to disk ─────────────────────────────────────────────────────

@router.post("/admin/backups/create")
@limiter.limit("10/minute")
async def create_backup(
    request: Request,
    destination_path: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        record = backup_service.create_backup(destination_path, db)
        return JSONResponse(
            {
                "ok": True,
                "message": f"Backup creado: {record.filename}",
                "filename": record.filename,
                "size_bytes": record.size_bytes,
                "id": record.id,
            }
        )
    except Exception as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=500)


# ── Download backup directly from browser ────────────────────────────────────

@router.get("/admin/backups/download-new")
@limiter.limit("10/minute")
async def download_new_backup(request: Request, db: Session = Depends(get_db)):
    filename, data = backup_service.create_download_backup(db)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Download existing backup from disk ────────────────────────────────────────

@router.get("/admin/backups/{backup_id}/download")
@limiter.limit("10/minute")
async def download_backup_by_id(
    backup_id: int, request: Request, db: Session = Depends(get_db)
):
    record = backup_service.get_backup(backup_id, db)
    if not record:
        return JSONResponse({"detail": "Backup no encontrado"}, status_code=404)
    from pathlib import Path
    fp = Path(record.full_path)
    if not fp.exists():
        return JSONResponse(
            {"detail": "Archivo no encontrado en disco. Puede que haya sido movido o eliminado."},
            status_code=404,
        )
    data = fp.read_bytes()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'},
    )


# ── Restore from uploaded ZIP ─────────────────────────────────────────────────

@router.post("/admin/backups/restore-upload")
@limiter.limit("5/minute")
async def restore_from_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if not backup_service.validate_backup_zip_bytes(data):
        return JSONResponse(
            {"ok": False, "message": "ZIP inválido: no contiene app.db"},
            status_code=400,
        )
    try:
        backup_service.restore_backup_bytes(data)
        return JSONResponse(
            {
                "ok": True,
                "message": (
                    "Restauración completada. "
                    "Reinicia la aplicación para aplicar todos los cambios."
                ),
            }
        )
    except Exception as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=500)


# ── Restore from local path ───────────────────────────────────────────────────

@router.post("/admin/backups/restore-path")
@limiter.limit("5/minute")
async def restore_from_path(
    request: Request,
    zip_path: str = Form(...),
    db: Session = Depends(get_db),
):
    from pathlib import Path
    p = Path(zip_path)
    if not p.exists():
        return JSONResponse(
            {"ok": False, "message": f"Ruta no encontrada: {zip_path}"},
            status_code=400,
        )
    if not backup_service.validate_backup_zip_path(p):
        return JSONResponse(
            {"ok": False, "message": "ZIP inválido: no contiene app.db"},
            status_code=400,
        )
    try:
        backup_service.restore_backup_from_path(p)
        return JSONResponse(
            {
                "ok": True,
                "message": (
                    "Restauración completada. "
                    "Reinicia la aplicación para aplicar todos los cambios."
                ),
            }
        )
    except Exception as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=500)


# ── Delete backup record ──────────────────────────────────────────────────────

@router.delete("/admin/backups/{backup_id}")
@limiter.limit("20/minute")
async def delete_backup(
    backup_id: int, request: Request, db: Session = Depends(get_db)
):
    ok = backup_service.delete_backup_record(backup_id, db)
    if not ok:
        return JSONResponse({"detail": "Backup no encontrado"}, status_code=404)
    return JSONResponse({"ok": True})
