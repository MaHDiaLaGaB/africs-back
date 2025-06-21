from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class TransactionCurrencyLot(Base):
    __tablename__ = "transaction_currency_lots"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False
    )
    lot_id = Column(
        Integer,
        ForeignKey("currency_lots.id", ondelete="CASCADE"),
        nullable=False
    )

    # الكمية المأخوذة من هذه الدفعة ضمن المعاملة
    quantity = Column(Float, nullable=False)

    # تكلفة الوحدة الأصلية في هذه الدفعة (لأغراض حساب الربح)
    cost_per_unit = Column(Float, nullable=False)

    # العلاقات للتسهيل عند الاستعلام
    transaction = relationship("Transaction", back_populates="lot_details")
    lot = relationship("CurrencyLot", back_populates="transaction_details")
