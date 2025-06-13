from sqlalchemy import Column, Integer, String, Float, Boolean
from app.db.session import Base


class Currency(Base):
    __tablename__ = "currencies"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # مثل USD, EUR
    exchange_rate = Column(Float, nullable=False)  # سعر البيع بالدينار الليبي
    symbol = Column(String, nullable=False)
    cost_per_unit = Column(Float, nullable=False)  # تكلفة شراء الوحدة (بالدينار الليبي)
    stock = Column(Float, default=0.0)  # الكمية المتوفرة (مثلاً 1000 USD)
    is_active = Column(Boolean, default=True)  # فعّالة / متوقفة مؤقتًا
