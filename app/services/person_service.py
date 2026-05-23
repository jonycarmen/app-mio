from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import BankAccount, Document, PayrollEntry, Person, WalletAddress
from app.schemas.person import PersonCreate, PersonUpdate, PublicPersonUpdate


def _clean_bank_accounts(items):
    return [item for item in items if item.iban or item.account_number or item.bank_name]


def _clean_wallets(items):
    return [item for item in items if item.address]


def generate_access_token():
    return str(uuid4())


def list_people(db: Session, q: str | None = None):
    stmt = (
        select(Person)
        .options(
            selectinload(Person.bank_accounts),
            selectinload(Person.wallet_addresses),
            selectinload(Person.documents),
            selectinload(Person.payroll_entries),
        )
        .order_by(Person.full_name.asc())
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Person.full_name.ilike(pattern),
                Person.dni.ilike(pattern),
                Person.passport.ilike(pattern),
                Person.bank_accounts.any(BankAccount.iban.ilike(pattern)),
                Person.wallet_addresses.any(WalletAddress.address.ilike(pattern)),
            )
        )

    people = db.scalars(stmt).all()
    result = []
    for person in people:
        latest = sorted(
            person.payroll_entries,
            key=lambda item: (item.effective_date, item.created_at),
            reverse=True,
        )
        current = latest[0] if latest else None
        result.append(
            {
                "id": person.id,
                "full_name": person.full_name,
                "dni": person.dni,
                "passport": person.passport,
                "access_token": person.access_token,
                "document_count": len(person.documents),
                "current_payroll": (
                    {"amount": current.amount, "effective_date": current.effective_date} if current else None
                ),
            }
        )
    return result


def get_person(db: Session, person_id: int):
    return db.scalar(
        select(Person)
        .options(
            selectinload(Person.bank_accounts),
            selectinload(Person.wallet_addresses),
            selectinload(Person.documents),
            selectinload(Person.payroll_entries),
        )
        .where(Person.id == person_id)
    )


def get_person_by_token(db: Session, token: str):
    return db.scalar(
        select(Person)
        .options(
            selectinload(Person.bank_accounts),
            selectinload(Person.wallet_addresses),
            selectinload(Person.documents),
            selectinload(Person.payroll_entries),
        )
        .where(Person.access_token == token)
    )


def ensure_access_token(db: Session, person: Person):
    if person.access_token:
        return person.access_token
    person.access_token = generate_access_token()
    db.add(person)
    db.commit()
    db.refresh(person)
    return person.access_token


def create_person(db: Session, payload: PersonCreate):
    person = Person(
        full_name=payload.full_name,
        dni=payload.dni,
        passport=payload.passport,
        access_token=generate_access_token(),
    )
    person.bank_accounts = [BankAccount(**item.model_dump()) for item in _clean_bank_accounts(payload.bank_accounts)]
    person.wallet_addresses = [WalletAddress(**item.model_dump()) for item in _clean_wallets(payload.wallet_addresses)]
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def update_person(db: Session, person: Person, payload: PersonUpdate):
    person.full_name = payload.full_name
    person.dni = payload.dni
    person.passport = payload.passport
    if not person.access_token:
        person.access_token = generate_access_token()
    person.bank_accounts.clear()
    person.wallet_addresses.clear()
    person.bank_accounts.extend([BankAccount(**item.model_dump()) for item in _clean_bank_accounts(payload.bank_accounts)])
    person.wallet_addresses.extend([WalletAddress(**item.model_dump()) for item in _clean_wallets(payload.wallet_addresses)])
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def update_public_person(db: Session, person: Person, payload: PublicPersonUpdate):
    person.dni = payload.dni
    person.passport = payload.passport
    if not person.access_token:
        person.access_token = generate_access_token()
    person.bank_accounts.clear()
    person.wallet_addresses.clear()
    person.bank_accounts.extend([BankAccount(**item.model_dump()) for item in _clean_bank_accounts(payload.bank_accounts)])
    person.wallet_addresses.extend([WalletAddress(**item.model_dump()) for item in _clean_wallets(payload.wallet_addresses)])
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def regenerate_access_token(db: Session, person: Person):
    person.access_token = generate_access_token()
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def delete_person(db: Session, person: Person):
    db.delete(person)
    db.commit()