from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class TransactionCurrencyLot(Base):
    __tablename__ = "transaction_currency_lots"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(
        Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    lot_id = Column(
        Integer, ForeignKey("currency_lots.id", ondelete="CASCADE"), nullable=False
    )

    quantity = Column(Float, nullable=False)

    cost_per_unit = Column(Float, nullable=False)

    transaction = relationship(
        "Transaction", back_populates="lot_details", passive_deletes=True
    )
    lot = relationship(
        "CurrencyLot",
        back_populates="transaction_details",
        lazy="joined",
        passive_deletes=True,
    )
