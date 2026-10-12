from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.payment_record import PaymentRecord
from app.models.salon import Salon, SubscriptionPlan
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.payment import (
    AdminPaymentCreate,
    AdminPaymentRecordOut,
    AdminRevenueSummaryOut,
    CurrencyRevenueTotal,
)


def _record_out(
    record: PaymentRecord,
    *,
    salon_name: str,
    recorded_by_email: str,
) -> AdminPaymentRecordOut:
    return AdminPaymentRecordOut(
        id=record.id,
        salon_id=record.salon_id,
        salon_name=salon_name,
        recorded_by_email=recorded_by_email,
        plan=record.plan,
        amount=record.amount,
        currency=record.currency,
        payment_method=record.payment_method,
        reference=record.reference,
        notes=record.notes,
        period_days=record.period_days,
        status=record.status,
        received_at=record.received_at,
    )


def record_verified_payment_and_activate(
    db: Session,
    payload: AdminPaymentCreate,
    admin: User,
) -> AdminPaymentRecordOut:
    """Record a receipt confirmed by a human and activate access in one transaction."""
    salon = db.get(Salon, payload.salon_id)
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")

    now = datetime.now(timezone.utc)
    subscription = db.execute(
        select(Subscription)
        .where(Subscription.salon_id == payload.salon_id)
        .with_for_update()
    ).scalar_one_or_none()

    if subscription is None:
        subscription = Subscription(
            salon_id=payload.salon_id,
            plan=salon.subscription_plan.value,
            status="active",
            usage_period_start=now.date().replace(day=1),
            beauty_jobs_used=0,
            current_period_end=None,
        )
        db.add(subscription)
        db.flush()

    current_end = subscription.current_period_end
    if current_end is not None and current_end.tzinfo is None:
        current_end = current_end.replace(tzinfo=timezone.utc)
    extension_start = (
        current_end
        if subscription.status in {"active", "trialing"} and current_end is not None and current_end > now
        else now
    )

    plan = SubscriptionPlan(payload.plan)
    subscription.plan = plan.value
    subscription.status = "active"
    subscription.current_period_end = extension_start + timedelta(days=payload.period_days)
    subscription.usage_period_start = now.date().replace(day=1)
    subscription.beauty_jobs_used = 0
    salon.subscription_plan = plan

    record = PaymentRecord(
        salon_id=salon.id,
        subscription_id=subscription.id,
        recorded_by_user_id=admin.id,
        plan=plan.value,
        amount=payload.amount,
        currency=payload.currency,
        payment_method=payload.payment_method,
        reference=payload.reference,
        notes=payload.notes,
        period_days=payload.period_days,
        status="confirmed",
        received_at=now,
    )
    db.add(record)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if payload.reference:
            duplicate = db.execute(
                select(PaymentRecord.id).where(
                    PaymentRecord.payment_method == payload.payment_method,
                    PaymentRecord.reference == payload.reference,
                )
            ).scalar_one_or_none()
            if duplicate is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This payment reference has already been recorded for that payment method.",
                ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment was not recorded because it conflicts with an existing record.",
        ) from exc

    db.refresh(record)
    return _record_out(record, salon_name=salon.name, recorded_by_email=admin.email)


def get_revenue_summary(
    db: Session,
    *,
    period: str,
) -> AdminRevenueSummaryOut:
    """Summarize manually verified receipts; no unconfirmed estimates are counted."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    elif period == "year":
        start = start.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)
    else:
        raise ValueError("Revenue period must be 'month' or 'year'")

    filters = (
        PaymentRecord.status == "confirmed",
        PaymentRecord.received_at >= start,
        PaymentRecord.received_at < end,
    )
    aggregate_rows = db.execute(
        select(
            PaymentRecord.currency,
            func.count(PaymentRecord.id),
            func.sum(PaymentRecord.amount),
        )
        .where(*filters)
        .group_by(PaymentRecord.currency)
        .order_by(PaymentRecord.currency.asc())
    ).all()
    totals = [
        CurrencyRevenueTotal(
            currency=currency,
            transaction_count=int(count),
            collected_total=Decimal(total or 0),
        )
        for currency, count, total in aggregate_rows
    ]

    recent_rows = db.execute(
        select(PaymentRecord, Salon.name, User.email)
        .join(Salon, Salon.id == PaymentRecord.salon_id)
        .join(User, User.id == PaymentRecord.recorded_by_user_id)
        .where(*filters)
        .order_by(PaymentRecord.received_at.desc())
        .limit(100)
    ).all()
    records = [
        _record_out(record, salon_name=salon_name, recorded_by_email=admin_email)
        for record, salon_name, admin_email in recent_rows
    ]

    return AdminRevenueSummaryOut(
        period=period,  # type: ignore[arg-type]
        period_start=start,
        period_end=end,
        transaction_count=sum(item.transaction_count for item in totals),
        totals_by_currency=totals,
        recent_payments=records,
    )
