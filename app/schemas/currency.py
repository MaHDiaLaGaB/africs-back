from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CurrencyCreate(BaseModel):
    name: str
    symbol: str

class CurrencyUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    is_active: Optional[bool] = None

class CurrencyOut(BaseModel):
    id: int
    name: str
    symbol: str
    is_active: bool
    stock: float  # comes from the @property on your ORM model

    class Config:
        from_attributes = True


# app/schemas/currency.py
class CurrencyLotLogOut(BaseModel):
    id: int
    lot_id: int
    currency_id: int
    quantity_added: float
    cost_per_unit: float
    created_at: datetime

    class Config:
        from_attributes = True
