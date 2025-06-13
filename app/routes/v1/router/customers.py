from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.customers import Customer
from app.models.transactions import Transaction
from app.models.receipt import ReceiptOrder
from app.schemas.customers import CustomerCreate, CustomerOut
from app.dependencies import get_db

router = APIRouter()


@router.get("/get", response_model=List[CustomerOut])
def get_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()


@router.post("/create", response_model=CustomerOut)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(**data.dict())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/{customer_id}/transactions")
def get_customer_transactions(customer_id: int, db: Session = Depends(get_db)):
    return db.query(Transaction).filter(
        Transaction.customer_id == customer_id,
        Transaction.payment_type == "credit"
    ).order_by(Transaction.created_at.desc()).all()


@router.get("/{customer_id}/receipts")
def get_customer_receipts(customer_id: int, db: Session = Depends(get_db)):
    return db.query(ReceiptOrder).filter(
        ReceiptOrder.customer_id == customer_id
    ).order_by(ReceiptOrder.created_at.desc()).all()
