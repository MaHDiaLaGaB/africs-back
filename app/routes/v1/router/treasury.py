from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.core.security import get_current_user
from app.models.users import User
from app.services.treasury_service import get_employee_balance


router = APIRouter()


@router.get("/get/{employee_id}")
async def read_balance(employee_id: int, db: Session = Depends(get_db)):
    try:
        balance = get_employee_balance(db, employee_id)
        return {"employee_id": employee_id, "balance": balance}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/me")
async def read_my_balance(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        balance = get_employee_balance(db, str(current_user.id))
        return {"employee_id": str(current_user.id), "balance": balance}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
