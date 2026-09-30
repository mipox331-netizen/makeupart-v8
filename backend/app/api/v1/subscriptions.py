from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.subscription import SubscriptionUsageOut
from app.services.subscription import get_subscription_snapshot

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/me", response_model=SubscriptionUsageOut)
def read_subscription_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SubscriptionUsageOut:
    return SubscriptionUsageOut(**get_subscription_snapshot(db, current_user.salon_id))
