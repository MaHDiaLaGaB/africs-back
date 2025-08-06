from pydantic import BaseModel
from datetime import datetime


class CurrencyLotCreate(BaseModel):
    quantity: float
    cost_per_unit: float


class CurrencyLotOut(BaseModel):
    id: int
    quantity: float
    remaining_quantity: float
    cost_per_unit: float
    created_at: datetime

    class Config:
        from_attributes = True
