from datetime import date, datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.salon import SubscriptionPlan


class SubscriptionUsageOut(BaseModel):
    plan: str
    status: str
    monthly_limit: int | None
    used: int
    remaining: int | None
    period_start: date
    current_period_end: datetime | None


class AdminSubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    salon_id: uuid.UUID
    salon_name: str
    owner_email: str | None
    plan: str
    status: str
    current_period_end: datetime | None
    days_remaining: int | None


class AdminSubscriptionActivate(BaseModel):
    plan: SubscriptionPlan = SubscriptionPlan.BASIC
    days: int = Field(default=30, ge=1, le=3660)
