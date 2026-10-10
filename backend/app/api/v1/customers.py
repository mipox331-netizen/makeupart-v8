import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.config import settings
from app.crud.customer import create_customer, get_customer, list_customers, update_customer
from app.db.session import get_db
from app.models.beauty_job import BeautyJob
from app.models.consent import ConsentRecord
from app.models.consultation import Consultation
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services.media_volume import commit_media_volume

router = APIRouter(prefix="/customers", tags=["customers"])


def _delete_customer_media(db: Session, salon_id: uuid.UUID, customer_id: uuid.UUID) -> None:
    salon_root = (settings.media_root_path / "salons" / str(salon_id)).resolve()
    jobs = db.execute(
        select(BeautyJob).where(
            BeautyJob.salon_id == salon_id,
            BeautyJob.customer_id == customer_id,
        )
    ).scalars().all()

    for job in jobs:
        for stored_path in (job.input_file_path, job.output_file_path):
            if not stored_path:
                continue
            candidate = Path(stored_path).resolve()
            if salon_root in candidate.parents and candidate.is_file():
                try:
                    candidate.unlink()
                except OSError:
                    pass


@router.get("", response_model=list[CustomerOut])
def list_customer_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Customer]:
    return list_customers(db, current_user.salon_id)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer_record(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Customer:
    customer = create_customer(db, current_user.salon_id, **customer_in.model_dump())
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer_record(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Customer:
    customer = get_customer(db, customer_id)
    if customer is None or customer.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer_record(
    customer_id: uuid.UUID,
    customer_in: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Customer:
    customer = get_customer(db, customer_id)
    if customer is None or customer.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    customer = update_customer(db, customer, customer_in.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_record(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> None:
    customer = get_customer(db, customer_id)
    if customer is None or customer.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    _delete_customer_media(db, current_user.salon_id, customer.id)
    db.execute(
        delete(Consultation).where(
            Consultation.salon_id == current_user.salon_id,
            Consultation.customer_id == customer.id,
        )
    )
    db.execute(
        delete(ConsentRecord).where(
            ConsentRecord.salon_id == current_user.salon_id,
            ConsentRecord.customer_id == customer.id,
        )
    )
    db.execute(
        delete(BeautyJob).where(
            BeautyJob.salon_id == current_user.salon_id,
            BeautyJob.customer_id == customer.id,
        )
    )
    db.delete(customer)
    # Persist removed media on the mounted production volume as well.
    commit_media_volume()
    db.commit()
