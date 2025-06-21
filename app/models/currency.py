from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

class Currency(Base):
    __tablename__ = "currencies"

    id         = Column(Integer, primary_key=True)
    name       = Column(String, unique=True, nullable=False)
    symbol     = Column(String, nullable=False)
    is_active  = Column(Boolean, default=True)

    # direct lots relationship (1-to-many)
    lots = relationship(
        "CurrencyLot",
        back_populates="currency",
        cascade="all, delete-orphan",
    )

    @property
    def stock(self) -> float:
        """Total available qty across all lots."""
        return sum(lot.remaining_quantity for lot in self.lots)

