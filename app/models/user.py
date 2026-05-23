from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.invitation import Invitation


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("people.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(150))
    profile_photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    theme_color: Mapped[str] = mapped_column(String(20), default="#3563e9")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    admin_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    admin_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # FK to the invitation used for registration (nullable for pre-existing users)
    invitation_id: Mapped[int | None] = mapped_column(
        ForeignKey("invitations.id", ondelete="SET NULL"), nullable=True
    )

    person = relationship("Person", back_populates="user", foreign_keys=[person_id])
    invitation: Mapped["Invitation | None"] = relationship(
        "Invitation", foreign_keys=[invitation_id], back_populates="registered_users"
    )
