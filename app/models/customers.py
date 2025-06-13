from sqlalchemy import Column, Integer, String, Float
from app.db.session import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    city = Column(String)
    balance_due = Column(Float, default=0.0)
