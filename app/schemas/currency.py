from pydantic import BaseModel
from typing import Optional


class CurrencyCreate(BaseModel):
    name: str
    symbol: str
    exchange_rate: float
    cost_per_unit: float
    stock: float


class CurrencyUpdate(BaseModel):
    exchange_rate: Optional[float]
    cost_per_unit: Optional[float]


class CurrencyOut(BaseModel):
    id: int
    name: str
    symbol: str
    exchange_rate: float
    cost_per_unit: float
    stock: float
    is_active: bool

    class Config:
        from_attributes = True
