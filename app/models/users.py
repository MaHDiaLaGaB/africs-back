import enum
from sqlalchemy import Column, String, Integer, Boolean, Enum
from sqlalchemy.orm import relationship
from app.db.session import Base


class Role(str, enum.Enum):
    admin = "admin"
    employee = "employee"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    role = Column(Enum(Role), default=Role.employee)
    transactions = relationship("Transaction", back_populates="employee")
    treasury = relationship("Treasury", back_populates="employee", uselist=False)
    receipt_orders = relationship("ReceiptOrder", back_populates="employee")
