import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.crud.beauty_job import get_beauty_job
from app.crud.consent import get_active_consent
from app.crud.consultation import create_consultation, get_consultation, list_consultations
from app.crud.customer import get_customer
from app.db.session import get_db
from app.models.consultation import Consultation
from app.models.user import User
from app.schemas.consultation import ConsultationCreate, ConsultationOut

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.get("", response_model=list[ConsultationOut])
def list_consultation_records(
    customer_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Consultation]:
    if customer_id is not None:
        customer = get_customer(db, customer_id)
        if customer is None or customer.salon_id != current_user.salon_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        return [
            item
            for item in list_consultations(db, current_user.salon_id)
            if item.customer_id == customer_id
        ]
    return list_consultations(db, current_user.salon_id)


@router.post("", response_model=ConsultationOut, status_code=status.HTTP_201_CREATED)
def create_consultation_record(
    consultation_in: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Consultation:
    customer = get_customer(db, consultation_in.customer_id)
    if customer is None or customer.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    if customer.consent_required:
        if not consultation_in.consent_granted or get_active_consent(
            db, current_user.salon_id, customer.id
        ) is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active customer consent is required for this consultation",
            )

    payload = consultation_in.model_dump(exclude={"customer_id"})
    if consultation_in.beauty_job_id is not None:
        job = get_beauty_job(db, current_user.salon_id, consultation_in.beauty_job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beauty job not found")
        if job.customer_id not in (None, customer.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Beauty job belongs to a different customer",
            )
        payload["before_image_url"] = payload["before_image_url"] or job.before_image_url
        payload["after_image_url"] = payload["after_image_url"] or job.after_image_url

    consultation = create_consultation(
        db,
        current_user.salon_id,
        consultation_in.customer_id,
        payload,
    )
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("/{consultation_id}", response_model=ConsultationOut)
def get_consultation_record(
    consultation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Consultation:
    consultation = get_consultation(db, consultation_id)
    if consultation is None or consultation.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    return consultation
