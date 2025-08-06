# models/transaction_status_log.py
from sqlalchemy import Column, Integer, Enum, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
from app.schemas.transactions import TransactionStatus


class TransactionStatusLog(Base):
    __tablename__ = "transaction_status_logs"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    previous_status = Column(Enum(TransactionStatus), nullable=False)
    new_status = Column(Enum(TransactionStatus), nullable=False)
    reason = Column(Text, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="status_logs")
    user = relationship("User")
