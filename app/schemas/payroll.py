from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PayrollCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    effective_date: date
    notes: str | None = Field(default=None, max_length=512)


class PayrollOut(PayrollCreate):
    id: int
    person_id: int
    created_at: datetime

    model_config = {"from_attributes": True}