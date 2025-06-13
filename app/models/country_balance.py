from app.db.session import Base
from sqlalchemy import Integer, String, Float, Column


class CountryBalance(Base):
    __tablename__ = "country_balances"

    id = Column(Integer, primary_key=True)
    country = Column(String, unique=True)
    balance = Column(Float, default=0.0)
