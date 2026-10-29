import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PaidPlan = Literal["basic", "pro", "enterprise"]
PaymentMethod = Literal["mobile_money", "bank_transfer", "cash", "card", "manual"]


class AdminPaymentCreate(BaseModel):
    salon_id: uuid.UUID
    plan: PaidPlan
    amount: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=2)
    currency: str = Field(default="TZS", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    payment_method: PaymentMethod
    period_days: int = Field(default=30, ge=1, le=3660)
    reference: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> str:
        currency = str(value or "TZS").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Currency must be a valid three-letter code.")
        return currency

    @field_validator("reference", mode="before")
    @classmethod
    def normalize_reference(cls, value: object) -> str | None:
        if value is None:
            return None
        reference = str(value).strip()
        return reference or None

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> str | None:
        if value is None:
            return None
        notes = str(value).strip()
        return notes or None


class AdminPaymentRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    salon_id: uuid.UUID
    salon_name: str
    recorded_by_email: str
    plan: str
    amount: Decimal
    currency: str
    payment_method: str
    reference: str | None
    notes: str | None
    period_days: int
    status: str
    received_at: datetime


class CurrencyRevenueTotal(BaseModel):
    currency: str
    transaction_count: int
    collected_total: Decimal


class AdminRevenueSummaryOut(BaseModel):
    period: Literal["month", "year"]
    period_start: datetime
    period_end: datetime
    transaction_count: int
    totals_by_currency: list[CurrencyRevenueTotal]
    recent_payments: list[AdminPaymentRecordOut]
