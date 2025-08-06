from pydantic import BaseModel
from enum import Enum


class Role(str, Enum):
    admin = "admin"
    employee = "employee"


class UserBase(BaseModel):
    username: str
    full_name: str


class UserRoleUpdate(BaseModel):
    role: Role


class UserCreate(UserBase):
    password: str
    role: Role = Role.employee


class UserOut(UserBase):
    id: int
    role: Role

    class Config:
        from_attributes = True
