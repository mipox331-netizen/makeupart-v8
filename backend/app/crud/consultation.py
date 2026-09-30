import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consultation import Consultation


def create_consultation(db: Session, salon_id: uuid.UUID, customer_id: uuid.UUID, payload: dict) -> Consultation:
    consultation = Consultation(salon_id=salon_id, customer_id=customer_id, **payload)
    db.add(consultation)
    db.flush()
    return consultation


def get_consultation(db: Session, consultation_id: uuid.UUID) -> Consultation | None:
    return db.get(Consultation, consultation_id)


def list_consultations(db: Session, salon_id: uuid.UUID) -> list[Consultation]:
    stmt = select(Consultation).where(Consultation.salon_id == salon_id).order_by(Consultation.created_at.desc())
    return list(db.execute(stmt).scalars().all())
