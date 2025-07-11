from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Float,
    DateTime,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
from app.schemas.transactions import PaymentType, TransactionStatus
from sqlalchemy.ext.hybrid import hybrid_property


class Transaction(Base):
    __tablename__ = "transactions"

    id             = Column(Integer, primary_key=True, index=True)
    reference      = Column(String, unique=True, index=True)
    customer_name  = Column(String, nullable=True)
    to             = Column(String, nullable=True)
    number         = Column(String, nullable=True)
    amount_foreign = Column(Float, nullable=False)
    amount_lyd     = Column(Float, nullable=False)
    payment_type   = Column(SQLEnum(PaymentType), default=PaymentType.cash)
    status         = Column(SQLEnum(TransactionStatus), default=TransactionStatus.pending)
    status_reason  = Column(String, nullable=True)
    profit         = Column(Float, nullable=False, default=0.0)
    created_at     = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)

    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee    = relationship("User", back_populates="transactions")

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer    = relationship("Customer")

    service_id = Column(Integer, ForeignKey("services.id"))
    service    = relationship("Service")

    currency_id = Column(Integer, ForeignKey("currencies.id"))
    currency    = relationship("Currency")  # you may add back_populates="transactions" if desired

    status_logs = relationship(
        "TransactionStatusLog",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    lot_details = relationship(
        "TransactionCurrencyLot",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
    @hybrid_property
    def employee_name(self) -> str:
        # Will return the User.full_name for this transaction’s employee
        return self.employee.full_name

    @hybrid_property
    def client_name(self) -> Optional[str]:
        # Will return the Customer.name if customer_id is set
        return self.customer.name if self.customer else None

