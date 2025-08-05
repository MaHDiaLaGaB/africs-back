from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.websocket import manager
from app.schemas.users import UserCreate, UserOut, UserRoleUpdate
from app.services.auth_service import create_user, update_user_role, update_user_password, update_user_full_name
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

@router.post(
    "/register", 
    response_model=UserOut, 
    dependencies=[Depends(require_admin)]
)
async def register(
    user_data: UserCreate, 
    db: Session = Depends(get_db)
):
    """
    Admin-only: Create a new user account
    """
    created_user = create_user(db, user_data)
    # Notify the newly registered user
    # await manager.send_personal_message(
    #     created_user.id,
    #     {
    #         "type": "user_registered",
    #         "content": f"👤 تم إنشاء حسابك باسم {created_user.username} بنجاح"
    #     }
    # )
    return created_user

@router.get(
    "/me", 
    response_model=UserOut
)
def read_profile(
    current_user: User = Depends(get_current_user)
):
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role
    )

@router.post(
    "/login"
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user_record = db.query(User).filter(User.username == form_data.username).first()
    if not user_record or not verify_password(form_data.password, user_record.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user_record.id), "role": user_record.role})
    return {"access_token": token, "token_type": "bearer"}

@router.put(
    "/{user_id}/password",
    dependencies=[Depends(require_admin)],
    summary="Admin: تغيير كلمة مرور أي موظف"
)
async def admin_change_user_password(
    user_id: int,
    password_change: PasswordChange,
    admin_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Admin-only: Change any employee's password
    """
    updated_user = update_user_password(db, user_id, password_change.new_password)
    # Notify the admin who performed the change
    # await manager.send_personal_message(
    #     admin_user.id,
    #     {
    #         "type": "password_changed",
    #         "content": f"🔑 تم تغيير كلمة مرور المستخدم {updated_user.username} بنجاح"
    #     }
    # )
    return {"detail": f"Password for user {updated_user.username} updated successfully"}

@router.put(
    "/user/{user_id}/role", 
    response_model=UserOut
)
async def change_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Admin-only: Change the role of a specific user
    """
    updated_user = update_user_role(db, user_id, role_data.role)
    # Notify the user whose role was changed
    # await manager.send_personal_message(
    #     updated_user.id,
    #     {
    #         "type": "role_changed",
    #         "content": f"🔐 تم تغيير صلاحياتك إلى {role_data.role}"
    #     }
    # )
    return updated_user

@router.get(
    "/users", 
    response_model=list[UserOut]
)
def get_all_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Admin-only: Retrieve all employee users
    """
    return db.query(User).filter(User.role == "employee").all()


class UserUpdateName(BaseModel):
    full_name: str

@router.put("/{user_id}/name", summary="تحديث الاسم الكامل للمستخدم")
def change_full_name(
    user_id: int,
    payload: UserUpdateName = Body(...),
    db: Session = Depends(get_db),
):
    return update_user_full_name(db, user_id, payload.full_name)
