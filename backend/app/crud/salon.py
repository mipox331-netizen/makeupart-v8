import uuid
from sqlalchemy.orm import Session

from app.models.salon import Salon
from app.models.subscription import Subscription
from app.schemas.salon import SalonCreate, SalonUpdate


def create_salon(db: Session, salon_in: SalonCreate) -> Salon:
    salon = Salon(**salon_in.model_dump())
    db.add(salon)
    db.flush()
    db.add(
        Subscription(
            salon_id=salon.id,
            plan=salon.subscription_plan.value,
            status="active",
            current_period_end=None,
        )
    )
    db.flush()
    return salon


def get_salon(db: Session, salon_id: uuid.UUID) -> Salon | None:
    return db.get(Salon, salon_id)


def update_salon(db: Session, salon: Salon, salon_in: SalonUpdate) -> Salon:
    for field, value in salon_in.model_dump(exclude_unset=True).items():
        setattr(salon, field, value)
    db.add(salon)
    db.flush()
    return salon
