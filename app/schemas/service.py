from pydantic import BaseModel
from enum import Enum
from typing import Optional
from .country import CountryCreate


class OperationType(str, Enum):
    multiply = "multiply"
    divide = "divide"
    plus = "pluse"


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    image_url: Optional[str] = None # TODO make it upload image locally for now
    price: Optional[float] = None
    operation: Optional[OperationType] = None
    currency_id: Optional[int] = None
    is_active: Optional[bool] = None


class ServiceCreate(BaseModel):
    name: str
    image_url: Optional[str] # TODO make it upload image locally for now
    price: float
    operation: OperationType
    currency_id: int
    country_id: int
    country: CountryCreate  

class ServiceOut(BaseModel):
    id: int
    name: str
    image_url: Optional[str]
    price: float
    operation: OperationType
    currency_id: int
    country_id: int
    is_active: bool

    class Config:
        from_attributes = True
