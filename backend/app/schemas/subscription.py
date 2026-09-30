from datetime import date

from pydantic import BaseModel


class SubscriptionUsageOut(BaseModel):
    plan: str
    status: str
    monthly_limit: int | None
    used: int
    remaining: int | None
    period_start: date
