from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BankAccountBase(BaseModel):
    bank_name: str | None = Field(default=None, max_length=255)
    iban: str | None = Field(default=None, max_length=64)
    account_number: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=512)


class BankAccountOut(BankAccountBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WalletAddressBase(BaseModel):
    network: str | None = Field(default=None, max_length=64)
    address: str = Field(max_length=256)
    label: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=512)


class WalletAddressOut(WalletAddressBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PayrollSnapshot(BaseModel):
    amount: Decimal
    effective_date: date


class PersonBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    dni: str | None = Field(default=None, max_length=64)
    passport: str | None = Field(default=None, max_length=64)


class PersonCreate(PersonBase):
    bank_accounts: list[BankAccountBase] = Field(default_factory=list)
    wallet_addresses: list[WalletAddressBase] = Field(default_factory=list)


class PersonUpdate(PersonBase):
    bank_accounts: list[BankAccountBase] = Field(default_factory=list)
    wallet_addresses: list[WalletAddressBase] = Field(default_factory=list)


class PersonListItem(PersonBase):
    id: int
    current_payroll: PayrollSnapshot | None = None
    document_count: int = 0
    access_token: str | None = None

    model_config = {"from_attributes": True}


class PersonOut(PersonBase):
    id: int
    access_token: str | None = None
    created_at: datetime
    updated_at: datetime
    bank_accounts: list[BankAccountOut]
    wallet_addresses: list[WalletAddressOut]

    model_config = {"from_attributes": True}


class PublicPersonUpdate(BaseModel):
    dni: str | None = Field(default=None, max_length=64)
    passport: str | None = Field(default=None, max_length=64)
    bank_accounts: list[BankAccountBase] = Field(default_factory=list)
    wallet_addresses: list[WalletAddressBase] = Field(default_factory=list)


class PublicPersonOut(BaseModel):
    full_name: str
    dni: str | None = None
    passport: str | None = None
    bank_accounts: list[BankAccountOut]
    wallet_addresses: list[WalletAddressOut]

    model_config = {"from_attributes": True}
