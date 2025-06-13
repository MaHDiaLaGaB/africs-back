from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class TreasuryTransfer(Base):
    __tablename__ = "treasury_transfers"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    from_employee_id = Column(Integer, ForeignKey("users.id"))
    to_employee_id = Column(Integer, ForeignKey("users.id"))

    from_employee = relationship("User", foreign_keys=[from_employee_id])
    to_employee = relationship("User", foreign_keys=[to_employee_id])
