from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.schemas.service import ServiceCreate, ServiceOut, ServiceUpdate
from app.dependencies import get_db
from app.models.service import Service
from app.core.security import require_admin, get_current_user
from app.services.treasury_service import transfer_amount
from app.core.websocket import manager
from app.models.transactions import Transaction
from app.models.users import User
from app.services.service_service import create_service


router = APIRouter()


@router.post(
    "/create", response_model=ServiceOut, dependencies=[Depends(require_admin)]
)
def add_service(data: ServiceCreate, db: Session = Depends(get_db)):
    return create_service(db, data)


@router.put(
    "/update/{service_id}",
    response_model=ServiceOut,
    dependencies=[Depends(require_admin)],
)
async def update_service(
    service_id: int, data: ServiceUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(service, field, value)

    db.commit()
    db.refresh(service)

    # إشعار الموظفين
    await manager.send_personal_message(message=f"🔔 تم تعديل الخدمة: {service.name}", user_id=current_user.id)

    return service


@router.delete("/delete/{service_id}", dependencies=[Depends(require_admin)])
async def delete_service(service_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    has_transactions = (
        db.query(Transaction).filter(Transaction.service_id == service_id).first()
    )
    if has_transactions:
        raise HTTPException(
            status_code=400, detail="❌ لا يمكن حذف الخدمة لأنها مرتبطة بحوالات موجودة."
        )

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    db.delete(service)
    db.commit()

    await manager.send_personal_message(message=f"🗑️ تم حذف الخدمة: {service.name}", user_id=current_user.id)

    return {"detail": f"✅ تم حذف الخدمة: {service.name}"}


@router.get("/available", response_model=List[ServiceOut])
def get_available_services(db: Session = Depends(get_db)):
    return db.query(Service).filter(Service.is_active == True).all()


@router.post("/transfer", dependencies=[Depends(require_admin)])
async def admin_transfer(
    from_employee_id: int,
    to_employee_id: int,
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = transfer_amount(db, from_employee_id, to_employee_id, amount)

    await manager.send_personal_message(
        message=f"💸 تم تحويل مبلغ {amount} LYD من موظف {from_employee_id} إلى {to_employee_id}",
        user_id=current_user.id
    )

    return {"detail": "✅ تم التحويل بنجاح", "transfer_id": transfer.id}
