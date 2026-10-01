import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_platform_admin
from app.db.session import get_db
from app.models.salon import SubscriptionPlan
from app.models.user import User
from app.schemas.subscription import AdminSubscriptionActivate, AdminSubscriptionOut, SubscriptionUsageOut
from app.services.subscription import (
    activate_subscription,
    get_subscription_snapshot,
    list_admin_subscriptions,
    suspend_subscription,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
admin_router = APIRouter(prefix="/admin/subscriptions", tags=["admin-subscriptions"])


@router.get("/me", response_model=SubscriptionUsageOut)
def read_subscription_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionUsageOut:
    return SubscriptionUsageOut(**get_subscription_snapshot(db, current_user.salon_id))


@admin_router.get("", response_model=list[AdminSubscriptionOut])
def admin_list_subscriptions(
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> list[AdminSubscriptionOut]:
    return list_admin_subscriptions(db)


@admin_router.post("/{salon_id}/activate", response_model=AdminSubscriptionOut)
def admin_activate_subscription(
    salon_id: uuid.UUID,
    payload: AdminSubscriptionActivate,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> AdminSubscriptionOut:
    try:
        activate_subscription(db, salon_id, plan=payload.plan, days=payload.days)
    except HTTPException:
        raise
    return next(row for row in list_admin_subscriptions(db) if row.salon_id == salon_id)


@admin_router.post("/{salon_id}/suspend", response_model=AdminSubscriptionOut)
def admin_suspend_subscription(
    salon_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> AdminSubscriptionOut:
    suspend_subscription(db, salon_id)
    return next(row for row in list_admin_subscriptions(db) if row.salon_id == salon_id)
