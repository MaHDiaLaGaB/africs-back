from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.currency import Currency


class CurrencyLot(Base):
    __tablename__ = "currency_lots"

    id = Column(Integer, primary_key=True)
    currency_id = Column(
        Integer, ForeignKey("currencies.id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Float, nullable=False)
    remaining_quantity = Column(Float, nullable=False)
    cost_per_unit = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    currency = relationship("Currency", back_populates="lots", passive_deletes=True)
    transaction_details = relationship(
        "TransactionCurrencyLot",
        back_populates="lot",
        cascade="all, delete-orphan",
    )
    logs = relationship(
        "CurrencyLotLog", back_populates="lot", cascade="all, delete-orphan"
    )


class CurrencyLotLog(Base):
    __tablename__ = "currency_lot_logs"

    id = Column(Integer, primary_key=True, index=True)
    lot_id = Column(
        Integer, ForeignKey("currency_lots.id", ondelete="CASCADE"), nullable=False
    )
    currency_id = Column(
        Integer, ForeignKey("currencies.id", ondelete="CASCADE"), nullable=False
    )
    quantity_added = Column(Float, nullable=False)
    cost_per_unit = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lot = relationship("CurrencyLot", back_populates="logs")
    currency = relationship("Currency", back_populates="lot_logs")
