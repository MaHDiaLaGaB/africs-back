from fastapi import HTTPException
from app.models.users import User, Role
from app.schemas.users import UserCreate
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.models.treasury import Treasury

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_user(db: Session, user_data: UserCreate):
    hashed_password = pwd_context.hash(user_data.password)
    user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=Role.employee,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    treasury = Treasury(employee_id=user.id, balance=0.0)
    db.add(treasury)
    db.commit()
    return user


def update_user_password(db: Session, user_id: int, new_password: str) -> User:
    """
    يحدّث كلمة مرور المستخدم (الموظف) المحدد بالمعرف user_id.
    يحمّل كلمة المرور الجديدة ويخزّنها بعد تجزئتها.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    hashed = pwd_context.hash(new_password)
    user.hashed_password = hashed

    db.add(user)
    db.commit()
    db.refresh(user)
    return user



def update_user_role(db: Session, user_id: int, new_role: Role):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = new_role
    db.commit()
    db.refresh(user)
    return user


def update_user_full_name(db: Session, user_id: int, new_full_name: str) -> User:
    """
    يحدث الاسم الكامل (full_name) للمستخدم المحدد بـ user_id.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.full_name = new_full_name
    db.commit()
    db.refresh(user)
    return user