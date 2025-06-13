from pydantic import BaseModel


class CustomerCreate(BaseModel):
    name: str
    phone: str
    city: str


class CustomerOut(CustomerCreate):
    id: int
    balance_due: float

    class Config:
        from_attributes = True
