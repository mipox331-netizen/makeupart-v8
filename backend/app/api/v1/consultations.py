import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.crud.consultation import create_consultation, get_consultation, list_consultations
from app.db.session import get_db
from app.models.consultation import Consultation
from app.models.user import User
from app.schemas.consultation import ConsultationCreate, ConsultationOut

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.get("", response_model=list[ConsultationOut])
def list_consultation_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Consultation]:
    return list_consultations(db, current_user.salon_id)


@router.post("", response_model=ConsultationOut, status_code=status.HTTP_201_CREATED)
def create_consultation_record(
    consultation_in: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Consultation:
    consultation = create_consultation(db, current_user.salon_id, consultation_in.customer_id, consultation_in.model_dump(exclude={"customer_id"}))
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
