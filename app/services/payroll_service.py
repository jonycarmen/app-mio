from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PayrollEntry
from app.schemas.payroll import PayrollCreate


def list_payrolls(db: Session, person_id: int):
    return db.scalars(
        select(PayrollEntry)
        .where(PayrollEntry.person_id == person_id)
        .order_by(PayrollEntry.effective_date.desc(), PayrollEntry.created_at.desc())
    ).all()


def create_payroll(db: Session, person_id: int, payload: PayrollCreate):
    payroll = PayrollEntry(person_id=person_id, **payload.model_dump())
    db.add(payroll)
    db.commit()
    db.refresh(payroll)
    return payroll


def current_payroll(db: Session, person_id: int):
    return db.scalar(
        select(PayrollEntry)
        .where(PayrollEntry.person_id == person_id)
        .order_by(PayrollEntry.effective_date.desc(), PayrollEntry.created_at.desc())
    )


def delete_payroll(db: Session, payroll: PayrollEntry) -> None:
    db.delete(payroll)
    db.commit()