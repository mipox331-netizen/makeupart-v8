import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.beauty_job import BeautyJob


def list_beauty_jobs(
    db: Session,
    salon_id: uuid.UUID,
    *,
    customer_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[BeautyJob]:
    stmt = select(BeautyJob).where(BeautyJob.salon_id == salon_id)
    if customer_id is not None:
        stmt = stmt.where(BeautyJob.customer_id == customer_id)
    stmt = stmt.order_by(BeautyJob.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def get_beauty_job(db: Session, salon_id: uuid.UUID, job_id: uuid.UUID) -> BeautyJob | None:
    job = db.get(BeautyJob, job_id)
    if job is None or job.salon_id != salon_id:
        return None
    return job
