from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_platform_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.payment import AdminPaymentCreate, AdminPaymentRecordOut, AdminRevenueSummaryOut
from app.services.payments import get_revenue_summary, record_verified_payment_and_activate

router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])


@router.get("/summary", response_model=AdminRevenueSummaryOut)
def read_revenue_summary(
    period: Literal["month", "year"] = Query(default="month"),
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> AdminRevenueSummaryOut:
    return get_revenue_summary(db, period=period)


@router.post(
    "/record",
    response_model=AdminPaymentRecordOut,
    status_code=status.HTTP_201_CREATED,
)
def create_verified_payment(
    payload: AdminPaymentCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_platform_admin),
) -> AdminPaymentRecordOut:
    return record_verified_payment_and_activate(db, payload, current_admin)
