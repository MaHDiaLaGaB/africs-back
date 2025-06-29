from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class PaymentType(str, Enum):
    cash = "cash"
    credit = "credit"


class TransactionStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"
    returned = "returned"

class TransactionStatusUpdate(BaseModel):
    status: TransactionStatus
    reason: Optional[str] = None

class TransactionCreate(BaseModel):
    service_id: int
    amount_foreign: float
    payment_type: PaymentType
    customer_id: Optional[int] = None
    customer_name: str
    to: str
    number: str


class TransactionOut(TransactionCreate):
    id: int
    reference: str
    amount_lyd: float
    status: TransactionStatus
    created_at: datetime

    class Config:
        from_attributes = True
