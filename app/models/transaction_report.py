from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.orm import declarative_base
from app.schemas.transactions import TransactionStatus
from app.db.session import Base


class TransactionReport(Base):
    __tablename__ = "transaction_reports"
    __table_args__ = {"info": {"is_view": True}}

    transaction_id = Column(Integer, primary_key=True)
    reference = Column(String)
    created_at = Column(DateTime)
    status = Column(Enum(TransactionStatus))
    status_reason = Column(String)
    amount_foreign = Column(Float)
    amount_lyd = Column(Float)
    profit = Column(Float)

    customer_id = Column(Integer)
    customer_name = Column(String)
    customer_phone = Column(String)
    customer_city = Column(String)

    employee_id = Column(Integer)
    employee_username = Column(String)
    employee_full_name = Column(String)

    service_id = Column(Integer)
    service_name = Column(String)
    service_price = Column(Float)
    service_operation = Column(String)

    currency_id = Column(Integer)
    currency_name = Column(String)
    currency_symbol = Column(String)
