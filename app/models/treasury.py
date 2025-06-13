from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Treasury(Base):
    __tablename__ = "treasuries"

    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, default=0.0)

    employee_id = Column(Integer, ForeignKey("users.id"), unique=True)
    employee = relationship("User", back_populates="treasury")
