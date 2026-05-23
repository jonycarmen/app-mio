from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    app_name: Mapped[str] = mapped_column(String(100), default="People Manager")
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(20), default="#6366f1")
    secondary_color: Mapped[str] = mapped_column(String(20), default="#3563e9")
    welcome_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
