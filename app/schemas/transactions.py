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

class TransactionUpdate(BaseModel):
    reference:       Optional[str]            = None
    customer_name:   Optional[str]            = None
    to:              Optional[str]            = None
    number:          Optional[str]            = None
    amount_foreign:  Optional[float]          = None
    amount_lyd:      Optional[float]          = None
    payment_type:    Optional[PaymentType]    = None
    status:          Optional[TransactionStatus] = None
    status_reason:   Optional[str]            = None
    profit:          Optional[float]          = None
    service_id:      Optional[int]            = None
    currency_id:     Optional[int]            = None
    created_at:      Optional[datetime]       = None
    notes:           Optional[str]            = None


"""
{"reference":"MM4",
"customer_name":"HALIMA SULAIMAN",
"to":"PALMPAY",
"number":"9035941238",
"amount_foreign":150,
"amount_lyd":4000,
"payment_type":"credit",
"notes":""}


"""


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
    notes: Optional[str] = None


class TransactionOut(TransactionCreate):
    id: int
    reference: str
    amount_lyd: float
    status: TransactionStatus
    created_at: datetime
    employee_name: str
    client_name: Optional[str]

    class Config:
        from_attributes = True
