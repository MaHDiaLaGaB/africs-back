from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.websocket import manager
from app.schemas.users import UserCreate, UserOut, UserRoleUpdate
from app.services.auth_service import create_user, update_user_role, update_user_password
from app.dependencies import get_db
from app.models.users import User
from app.core.security import (
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
)


router = APIRouter()

class PasswordChange(BaseModel):
    new_password: str = Field(
        ..., 
        min_length=8, 
        description="New password, at least 8 characters"
    )


@router.post("/register", response_model=UserOut, dependencies=[Depends(require_admin)])
def register(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)



@router.get("/me")
def read_profile(user: User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.put(
    "/{user_id}/password",
    dependencies=[Depends(require_admin)],
    summary="Admin: تغيير كلمة مرور أي موظف"
)
async def admin_change_user_password(
    user_id: int,
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    يسمح للمسؤول (admin) بتغيير كلمة مرور موظف محدد.
    """
    # سيُرفع 404 إذا لم يوجد المستخدم
    user = update_user_password(db, user_id, payload.new_password)

    # إشعار للمسؤول بأن العملية نجحت
    await manager.send_personal_message(
        message=f"🔑 تم تغيير كلمة مرور المستخدم {user.username} بنجاح",
        user_id=current_user.id
    )
    return {"detail": f"Password for user {user.username} updated successfully"}


@router.put("/user/{user_id}/role", response_model=UserOut)
def change_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return update_user_role(db, user_id, role_update.role)


@router.get("/users", response_model=list[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    return db.query(User).filter(User.role == "employee").all()

