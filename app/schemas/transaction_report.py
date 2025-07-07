# app/schemas/transaction_report.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransactionReportOut(BaseModel):
    transaction_id: int
    reference: str
    created_at: datetime
    status: str
    status_reason: Optional[str]
    amount_foreign: float
    amount_lyd: float
    profit: float

    customer_id: Optional[int]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    customer_city: Optional[str]

    employee_id: int
    employee_username: str
    employee_full_name: str

    service_id: Optional[int]
    service_name: Optional[str]
    service_price: float
    service_operation: str

    currency_id: Optional[int]
    currency_name: str
    currency_symbol: str

    class Config:
        from_attributes = True
