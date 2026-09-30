import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.crud.consent import create_consent, get_active_consent, list_customer_consents
from app.crud.customer import get_customer
from app.db.session import get_db
from app.models.consent import ConsentRecord
from app.models.user import User
from app.schemas.consent import ConsentCreate, ConsentOut

router = APIRouter(prefix="/consents", tags=["consents"])


def _customer_or_404(db: Session, current_user: User, customer_id: uuid.UUID):
    customer = get_customer(db, customer_id)
    if customer is None or customer.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.get("/customer/{customer_id}", response_model=list[ConsentOut])
def list_customer_consent_records(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ConsentRecord]:
    _customer_or_404(db, current_user, customer_id)
    return list_customer_consents(db, current_user.salon_id, customer_id)


@router.get("/customer/{customer_id}/active", response_model=ConsentOut | None)
def get_customer_active_consent(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConsentRecord | None:
    _customer_or_404(db, current_user, customer_id)
    return get_active_consent(db, current_user.salon_id, customer_id)


@router.post("", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
def create_customer_consent(
    consent_in: ConsentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConsentRecord:
    _customer_or_404(db, current_user, consent_in.customer_id)
    record = create_consent(db, current_user.salon_id, **consent_in.model_dump())
    db.commit()
    db.refresh(record)
    return record
