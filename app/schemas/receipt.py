from pydantic import BaseModel
from datetime import datetime


class ReceiptCreate(BaseModel):
    customer_id: int
    amount: float


class ReceiptOut(BaseModel):
    id: int
    amount: float
    created_at: datetime
    customer_id: int
    employee_id: int

    class Config:
        from_attributes = True
