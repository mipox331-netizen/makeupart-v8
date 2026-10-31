from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.beauty_job import BeautyJob, BeautyJobStatus
from app.models.salon import Salon, SubscriptionPlan
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import AdminSubscriptionOut

PLAN_LIMITS: dict[SubscriptionPlan, int | None] = {
    SubscriptionPlan.FREE: 25,
    SubscriptionPlan.BASIC: 250,
    SubscriptionPlan.PRO: 1000,
    SubscriptionPlan.ENTERPRISE: None,
}

PLAN_MAKEUP_STYLES: dict[SubscriptionPlan, frozenset[str]] = {
    SubscriptionPlan.FREE: frozenset({"natural", "skin_only"}),
    SubscriptionPlan.BASIC: frozenset({"natural", "soft_glam", "skin_only"}),
    SubscriptionPlan.PRO: frozenset({
        "natural", "soft_glam", "bridal_rose", "evening_glam",
        "smokey_eye", "cat_eye", "eyeshadow", "eyeliner", "lipstick", "blush", "skin_only",
    }),
    SubscriptionPlan.ENTERPRISE: frozenset({
        "natural", "soft_glam", "bridal_rose", "evening_glam",
        "smokey_eye", "cat_eye", "eyeshadow", "eyeliner", "lipstick", "blush", "skin_only",
    }),
}

PLAN_PHOTO_FINISHES: dict[SubscriptionPlan, frozenset[str]] = {
    SubscriptionPlan.FREE: frozenset({"Natural Finish", "Warm Glow"}),
    SubscriptionPlan.BASIC: frozenset({"Natural Finish", "Warm Glow", "Soft Glam"}),
    SubscriptionPlan.PRO: frozenset({
        "Natural Finish", "Warm Glow", "Soft Glam", "Studio Polish", "Golden Hour",
    }),
    SubscriptionPlan.ENTERPRISE: frozenset({
        "Natural Finish", "Warm Glow", "Soft Glam", "Studio Polish", "Golden Hour",
    }),
}

PLAN_GENERATIVE_ENTITLED = frozenset({SubscriptionPlan.PRO, SubscriptionPlan.ENTERPRISE})

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _normalise_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _get_subscription(db: Session, salon_id, *, lock: bool = False) -> Subscription:
    # A FOR UPDATE on a missing subscription row locks nothing. During first
    # use, simultaneous requests could therefore both try to insert the salon's
    # one allowed subscription and one would fail the unique salon_id constraint.
    # Lock the stable parent salon row before creating a missing subscription.
    # This also protects callers that do not otherwise need the subscription row
    # locked. Every first-creation path must take this parent lock and recheck.
    salon: Salon | None = None
    if lock:
        salon = db.execute(
            select(Salon).where(Salon.id == salon_id).with_for_update()
        ).scalars().first()
        if salon is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")

    statement = select(Subscription).where(Subscription.salon_id == salon_id)
    if lock:
        statement = statement.with_for_update()
    subscription = db.execute(statement).scalars().first()
    if subscription is not None:
        return subscription

    if salon is None:
        # A missing child row cannot be locked, so serialize creation through the
        # parent row, then re-read to observe a subscription created by a request
        # that held this lock before us.
        salon = db.execute(
            select(Salon).where(Salon.id == salon_id).with_for_update()
        ).scalars().first()
        if salon is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")
        statement = select(Subscription).where(Subscription.salon_id == salon_id)
        subscription = db.execute(statement).scalars().first()
        if subscription is not None:
            return subscription

    subscription = Subscription(
        salon_id=salon_id,
        plan=salon.subscription_plan.value,
        status="active" if salon.subscription_plan == SubscriptionPlan.FREE else "trialing",
        usage_period_start=_today().replace(day=1),
        current_period_end=(
            None
            if salon.subscription_plan == SubscriptionPlan.FREE
            else _now() + timedelta(days=settings.SUBSCRIPTION_TRIAL_DAYS)
        ),
        beauty_jobs_used=0,
    )
    db.add(subscription)
    db.flush()
    return subscription


def get_or_create_subscription_for_update(db: Session, salon_id) -> Subscription:
    """Return the salon subscription while holding the stable parent-row lock."""
    return _get_subscription(db, salon_id, lock=True)


def _reset_usage_period(subscription: Subscription) -> bool:
    month_start = _today().replace(day=1)
    if subscription.usage_period_start == month_start:
        return False
    subscription.usage_period_start = month_start
    subscription.beauty_jobs_used = 0
    return True


def _expire_if_due(subscription: Subscription) -> bool:
    # Free plans never expire. If an old row still carries an expiry date,
    # it came from the legacy 30-day free-plan lifecycle and should be reopened.
    # Explicit admin suspensions clear that date in suspend_subscription(),
    # so ordinary reads must not undo a deliberate suspension.
    if subscription.plan.lower() == SubscriptionPlan.FREE.value:
        changed = False
        if subscription.current_period_end is not None:
            subscription.current_period_end = None
            changed = True
            if subscription.status.lower() != "active":
                subscription.status = "active"
                changed = True
        elif subscription.status.lower() == "trialing":
            subscription.status = "active"
            changed = True
        return changed

    period_end = _normalise_dt(subscription.current_period_end)
    if (
        period_end is not None
        and period_end <= _now()
        and subscription.status.lower() in ACTIVE_SUBSCRIPTION_STATUSES
    ):
        subscription.status = "suspended"
        return True
    return False


def enforce_subscription_access(db: Session, user: User) -> Subscription:
    subscription = _get_subscription(db, user.salon_id, lock=True)
    changed = _expire_if_due(subscription)
    if changed:
        db.commit()
    if subscription.status.lower() not in ACTIVE_SUBSCRIPTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription expired or inactive. Please renew the salon subscription.",
        )
    return subscription


def _plan_for(subscription: Subscription, salon: Salon) -> SubscriptionPlan:
    try:
        return SubscriptionPlan(subscription.plan.lower())
    except ValueError:
        return salon.subscription_plan


def require_beauty_feature(
    db: Session,
    salon_id,
    *,
    feature_kind: str,
    feature_name: str,
) -> None:
    """Enforce plan entitlements on the server; client-side locks are UX only."""
    subscription = _get_subscription(db, salon_id, lock=True)
    if _expire_if_due(subscription):
        db.commit()
    if subscription.status.lower() not in ACTIVE_SUBSCRIPTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription is expired or inactive.",
        )

    salon = db.get(Salon, salon_id)
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")
    plan = _plan_for(subscription, salon)

    # Generative image providers can incur real per-image cost and send photos
    # to a third party. Enforce a paid-plan gate server-side even if a client
    # bypasses the visual lock or the provider key is configured later.
    if feature_kind == "generative_engine":
        if plan not in PLAN_GENERATIVE_ENTITLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Generative AI processing requires the Pro plan or higher.",
                headers={"X-Required-Plan": "pro"},
            )
        return

    if feature_kind == "makeup_style":
        entitled = PLAN_MAKEUP_STYLES[plan]
        label = "makeup style"
        required_plan = SubscriptionPlan.BASIC if plan == SubscriptionPlan.FREE and feature_name == "soft_glam" else SubscriptionPlan.PRO
    elif feature_kind == "photo_finish":
        entitled = PLAN_PHOTO_FINISHES[plan]
        label = "photo finish"
        required_plan = SubscriptionPlan.BASIC if plan == SubscriptionPlan.FREE and feature_name == "Soft Glam" else SubscriptionPlan.PRO
    else:
        raise ValueError(f"Unknown beauty feature kind: {feature_kind}")

    if feature_name not in entitled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"The {feature_name} {label} is included with the "
                f"{required_plan.value.title()} plan or higher. "
                "Contact your platform administrator to upgrade."
            ),
            headers={"X-Required-Plan": required_plan.value},
        )


def reserve_beauty_job_quota(db: Session, salon_id) -> None:
    subscription = _get_subscription(db, salon_id, lock=True)
    salon = db.get(Salon, salon_id)
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")

    _expire_if_due(subscription)
    _reset_usage_period(subscription)
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

    _expire_if_due(subscription)
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
        "current_period_end": subscription.current_period_end,
        "available_makeup_styles": sorted(PLAN_MAKEUP_STYLES[plan]),
        "available_photo_finishes": sorted(PLAN_PHOTO_FINISHES[plan]),
        "generative_engine_entitled": plan in PLAN_GENERATIVE_ENTITLED,
    }


def activate_subscription(db: Session, salon_id, *, plan: SubscriptionPlan, days: int) -> Subscription:
    subscription = _get_subscription(db, salon_id, lock=True)
    salon = db.get(Salon, salon_id)
    if salon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")

    now = _now()
    subscription.plan = plan.value
    subscription.status = "active"
    subscription.current_period_end = None if plan == SubscriptionPlan.FREE else now + timedelta(days=days)
    subscription.usage_period_start = now.date().replace(day=1)
    subscription.beauty_jobs_used = 0
    salon.subscription_plan = plan
    db.commit()
    db.refresh(subscription)
    return subscription


def suspend_subscription(db: Session, salon_id) -> Subscription:
    subscription = _get_subscription(db, salon_id, lock=True)
    subscription.status = "suspended"
    # Free plans have no billing expiry; clear legacy dates so a later read
    # can distinguish an explicit admin suspension from an expired legacy row.
    if subscription.plan.lower() == SubscriptionPlan.FREE.value:
        subscription.current_period_end = None
    db.commit()
    db.refresh(subscription)
    return subscription


def list_admin_subscriptions(db: Session) -> list[AdminSubscriptionOut]:
    salons = list(db.execute(select(Salon).order_by(Salon.created_at.desc())).scalars().all())
    rows: list[AdminSubscriptionOut] = []
    now = _now()

    for salon in salons:
        subscription = _get_subscription(db, salon.id, lock=True)
        if _expire_if_due(subscription):
            db.commit()
            db.refresh(subscription)

        owner = next((user for user in salon.users if user.role.value == "owner"), None)
        period_end = _normalise_dt(subscription.current_period_end)
        days_remaining = None
        if period_end is not None:
            days_remaining = max((period_end - now).days, 0)

        rows.append(
            AdminSubscriptionOut(
                salon_id=salon.id,
                salon_name=salon.name,
                owner_email=owner.email if owner else None,
                plan=subscription.plan,
                status=subscription.status,
                current_period_end=period_end,
                days_remaining=days_remaining,
            )
        )

    db.commit()
    return rows


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
