from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    dni: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    passport: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    access_token: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bank_accounts = relationship("BankAccount", back_populates="person", cascade="all, delete-orphan")
    wallet_addresses = relationship("WalletAddress", back_populates="person", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="person", cascade="all, delete-orphan")
    payroll_entries = relationship("PayrollEntry", back_populates="person", cascade="all, delete-orphan")
    user = relationship("User", back_populates="person", uselist=False)
