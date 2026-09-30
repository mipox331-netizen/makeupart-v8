from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.beauty_job import BeautyJob, BeautyJobStatus
from app.models.salon import Salon, SubscriptionPlan
from app.models.subscription import Subscription

PLAN_LIMITS: dict[SubscriptionPlan, int | None] = {
    SubscriptionPlan.FREE: 25,
    SubscriptionPlan.BASIC: 250,
    SubscriptionPlan.PRO: 1000,
    SubscriptionPlan.ENTERPRISE: None,
}

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _get_subscription(
    db: Session,
    salon_id,
    *,
    lock: bool = False,
) -> Subscription:
    statement = select(Subscription).where(Subscription.salon_id == salon_id)
    if lock:
        statement = statement.with_for_update()
    subscription = db.execute(statement).scalars().first()
    if subscription is not None:
        return subscription

    salon = db.get(Salon, salon_id)
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")

    subscription = Subscription(
        salon_id=salon_id,
        plan=salon.subscription_plan.value,
        status="active",
        usage_period_start=_today(),
        beauty_jobs_used=0,
    )
    db.add(subscription)
    db.flush()
    return subscription


def _reset_usage_period(subscription: Subscription) -> bool:
    today = _today()
    if subscription.usage_period_start == today.replace(day=1):
        return False
    subscription.usage_period_start = today.replace(day=1)
    subscription.beauty_jobs_used = 0
    return True


def _plan_for(subscription: Subscription, salon: Salon) -> SubscriptionPlan:
    try:
        return SubscriptionPlan(subscription.plan.lower())
    except ValueError:
        return salon.subscription_plan


def reserve_beauty_job_quota(db: Session, salon_id) -> None:
    subscription = _get_subscription(db, salon_id, lock=True)
    salon = db.get(Salon, salon_id)
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")

    changed = _reset_usage_period(subscription)
    plan = _plan_for(subscription, salon)
    limit = PLAN_LIMITS[plan]

    if subscription.status.lower() not in ACTIVE_SUBSCRIPTION_STATUSES:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription is not active",
        )

    if limit is not None and subscription.beauty_jobs_used >= limit:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly beauty processing quota reached for the {plan.value} plan.",
            headers={"X-Quota-Limit": str(limit), "X-Quota-Used": str(subscription.beauty_jobs_used)},
        )

    subscription.beauty_jobs_used += 1
    db.add(subscription)
    db.commit()


def release_beauty_job_quota(db: Session, salon_id) -> None:
    try:
        subscription = _get_subscription(db, salon_id, lock=True)
        if subscription.usage_period_start == _today().replace(day=1) and subscription.beauty_jobs_used > 0:
            subscription.beauty_jobs_used -= 1
        db.commit()
    except Exception:
        db.rollback()


def get_subscription_snapshot(db: Session, salon_id) -> dict:
    subscription = _get_subscription(db, salon_id, lock=True)
    salon = db.get(Salon, salon_id)
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")

    _reset_usage_period(subscription)
    plan = _plan_for(subscription, salon)
    limit = PLAN_LIMITS[plan]
    used = subscription.beauty_jobs_used
    remaining = None if limit is None else max(limit - used, 0)
    db.commit()

    return {
        "plan": plan.value,
        "status": subscription.status,
        "monthly_limit": limit,
        "used": used,
        "remaining": remaining,
        "period_start": subscription.usage_period_start,
    }


def count_completed_beauty_jobs(db: Session, salon_id, period_start: date) -> int:
    return int(
        db.execute(
            select(BeautyJob.id)
            .where(
                BeautyJob.salon_id == salon_id,
                BeautyJob.status == BeautyJobStatus.COMPLETED,
                BeautyJob.created_at >= period_start,
            )
        ).scalars().unique().all().__len__()
    )
