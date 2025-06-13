from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


class OperationType(str, enum.Enum):
    multiply = "multiply"
    divide = "divide"
    pluse = "pluse"


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    operation = Column(Enum(OperationType), nullable=False)

    currency_id = Column(Integer, ForeignKey("currencies.id"))
    currency = relationship("Currency")

    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    country = relationship("Country")

    is_active = Column(Boolean, default=True)
