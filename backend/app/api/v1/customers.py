import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.crud.customer import create_customer, get_customer, list_customers, update_customer
from app.db.session import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


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
