from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BackupRecord(Base):
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    destination_path: Mapped[str] = mapped_column(String(1024))
    full_path: Mapped[str] = mapped_column(String(1024), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    type: Mapped[str] = mapped_column(String(20), default="manual")   # manual | auto | download
    status: Mapped[str] = mapped_column(String(20), default="ok")      # ok | error
    notes: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
