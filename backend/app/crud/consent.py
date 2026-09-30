import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consent import ConsentRecord


def create_consent(
    db: Session,
    salon_id: uuid.UUID,
    *,
    customer_id: uuid.UUID,
    granted: bool,
    consent_text: str,
    notes: str | None = None,
    expires_at=None,
) -> ConsentRecord:
    record = ConsentRecord(
        salon_id=salon_id,
        customer_id=customer_id,
        granted=granted,
        consent_text=consent_text,
        notes=notes,
        expires_at=expires_at,
    )
    db.add(record)
    db.flush()
    return record


def get_active_consent(
    db: Session,
    salon_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> ConsentRecord | None:
    stmt = (
        select(ConsentRecord)
        .where(
            ConsentRecord.salon_id == salon_id,
            ConsentRecord.customer_id == customer_id,
        )
        .order_by(ConsentRecord.created_at.desc())
    )
    latest = db.execute(stmt).scalars().first()
    if latest is None or not latest.granted:
        return None
    if latest.expires_at is not None:
        expires_at = latest.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            return None
    return latest


def list_customer_consents(
    db: Session,
    salon_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> list[ConsentRecord]:
    stmt = (
        select(ConsentRecord)
        .where(
            ConsentRecord.salon_id == salon_id,
            ConsentRecord.customer_id == customer_id,
        )
        .order_by(ConsentRecord.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())
