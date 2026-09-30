import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def create_customer(db: Session, salon_id: uuid.UUID, *, first_name: str, last_name: str, email: str | None = None, phone: str | None = None, notes: str | None = None, consent_required: bool = True) -> Customer:
    customer = Customer(
        salon_id=salon_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        notes=notes,
        consent_required=consent_required,
    )
    db.add(customer)
    db.flush()
    return customer


def get_customer(db: Session, customer_id: uuid.UUID) -> Customer | None:
    return db.get(Customer, customer_id)


def list_customers(db: Session, salon_id: uuid.UUID) -> list[Customer]:
    stmt = select(Customer).where(Customer.salon_id == salon_id).order_by(Customer.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def update_customer(db: Session, customer: Customer, payload: dict) -> Customer:
    for field, value in payload.items():
        if value is not None:
            setattr(customer, field, value)
    db.add(customer)
    db.flush()
    return customer
