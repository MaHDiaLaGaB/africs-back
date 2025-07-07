from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.currency import Currency
from app.models.currency_lot import CurrencyLot
from app.schemas.currency_lot import CurrencyLotOut, CurrencyLotCreate
from app.schemas.currency import CurrencyCreate, CurrencyUpdate, CurrencyOut
from app.dependencies import get_db
from app.core.security import require_admin
from app.core.websocket import manager
from app.models.users import User

router = APIRouter()

@router.get("/currencies/get", response_model=List[CurrencyOut])
def get_all_currencies(
    db: Session = Depends(get_db)
):
    return db.query(Currency).all()

@router.get("/currencies/{currency_id}", response_model=CurrencyOut)
def get_currency(
    currency_id: int,
    db: Session = Depends(get_db)
):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    return currency

@router.post(
    "/currencies/create", 
    response_model=CurrencyOut, 
    dependencies=[Depends(require_admin)]
)
async def create_currency(
    currency_data: CurrencyCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    new_currency = Currency(**currency_data.dict())
    db.add(new_currency)
    db.commit()
    db.refresh(new_currency)

    # Notify admin about the new currency
    await manager.send_personal_message(
        admin_user.id,
        {
            "type": "currency_created",
            "content": f"💱 تم إضافة عملة جديدة: {new_currency.name}"
        }
    )

    return new_currency

@router.put(
    "/currencies/{currency_id}", 
    response_model=CurrencyOut, 
    dependencies=[Depends(require_admin)]
)
async def update_currency(
    currency_id: int,
    currency_data: CurrencyUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")

    for field, value in currency_data.dict(exclude_unset=True).items():
        setattr(currency, field, value)

    db.commit()
    db.refresh(currency)

    # Notify admin about the update
    await manager.send_personal_message(
        admin_user.id,
        {
            "type": "currency_updated",
            "content": f"💱 تم تحديث بيانات العملة: {currency.name}"
        }
    )

    return currency

@router.post(
    "/currencies/{currency_id}/lots",
    response_model=CurrencyLotOut,
    dependencies=[Depends(require_admin)],
)
async def add_currency_lot(
    currency_id: int,
    lot_data: CurrencyLotCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")

    new_lot = CurrencyLot(
        currency_id=currency_id,
        quantity=lot_data.quantity,
        remaining_quantity=lot_data.quantity,
        cost_per_unit=lot_data.cost_per_unit,
    )
    db.add(new_lot)
    db.commit()
    db.refresh(new_lot)

    # Notify admin about the new lot
    await manager.send_personal_message(
        admin_user.id,
        {
            "type": "currency_lot_added",
            "content": (
                f"📦 تم إضافة دفعة جديدة للعملة {currency.name}: "
                f"الكمية {new_lot.quantity} وحدة"
            )
        }
    )

    return new_lot
