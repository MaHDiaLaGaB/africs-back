from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, JSON
from datetime import datetime
from app.db.session import Base


class TransactionAudit(Base):
    __tablename__ = "transaction_audits"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    old_status = Column(String)
    new_status = Column(String)
    reason = Column(String)
    modified_by = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    changes = Column(JSON)
