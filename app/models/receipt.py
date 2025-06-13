from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class ReceiptOrder(Base):
    __tablename__ = "receipt_orders"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer_id = Column(Integer, ForeignKey("customers.id"))
    customer = relationship("Customer")

    employee_id = Column(Integer, ForeignKey("users.id"))
    employee = relationship("User", back_populates="receipt_orders")
