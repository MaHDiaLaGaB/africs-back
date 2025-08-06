from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.models.currency import Currency
from app.models.currency_lot import CurrencyLot, CurrencyLotLog
from app.schemas.currency_lot import CurrencyLotOut, CurrencyLotCreate
from app.schemas.currency import CurrencyCreate, CurrencyUpdate, CurrencyOut
from app.dependencies import get_db
from app.core.security import require_admin
from app.core.websocket import manager
from app.schemas.currency import CurrencyLotLogOut
from app.models.users import User

router = APIRouter()


@router.get("/currencies/get", response_model=List[CurrencyOut])
def get_all_currencies(db: Session = Depends(get_db)):
    return db.query(Currency).all()


@router.get("/currencies/{currency_id}", response_model=CurrencyOut)
def get_currency(currency_id: int, db: Session = Depends(get_db)):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    return currency


@router.get("/{currency_id}/lots", response_model=List[CurrencyLotOut])
def get_currency_lots(currency_id: int, db: Session = Depends(get_db)):
    lots = (
        db.query(CurrencyLot)
        .filter(CurrencyLot.currency_id == currency_id)
        .order_by(CurrencyLot.created_at)
        .all()
    )
    if lots is None:
        raise HTTPException(404, "Currency not found or no lots")
    return lots


@router.post(
    "/currencies/create",
    response_model=CurrencyOut,
    dependencies=[Depends(require_admin)],
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

    # Broadcast to all users
    await manager.broadcast(
        {
            "type": "currency_created",
            "content": f"💱 تم إضافة عملة جديدة: {new_currency.name}",
        }
    )

    return new_currency


@router.put(
    "/currencies/{currency_id}",
    response_model=CurrencyOut,
    dependencies=[Depends(require_admin)],
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

    # Broadcast to all users
    await manager.broadcast(
        {
            "type": "currency_updated",
            "content": f"💱 تم تحديث بيانات العملة: {currency.name}",
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

    # ✅ 1. حساب العجز الحالي في العملة (كمية سالبة)
    total_deficit = (
        db.query(func.sum(CurrencyLot.remaining_quantity))
        .filter(
            CurrencyLot.currency_id == currency_id, CurrencyLot.remaining_quantity < 0
        )
        .scalar()
        or 0
    )

    total_deficit = abs(total_deficit)

    # ✅ 2. خصم العجز من الكمية الجديدة
    adjusted_remaining = lot_data.quantity - total_deficit
    if adjusted_remaining < 0:
        adjusted_remaining = 0

    # ✅ 3. إنشاء الدفعة مع الكمية المعدلة
    new_lot = CurrencyLot(
        currency_id=currency_id,
        quantity=lot_data.quantity,
        remaining_quantity=adjusted_remaining,
        cost_per_unit=lot_data.cost_per_unit,
    )
    db.add(new_lot)

    # ✅ 4. تصفير الكميات السالبة من الـ lots السابقة (اختياري، لتكون أنظف)
    negative_lots = (
        db.query(CurrencyLot)
        .filter(
            CurrencyLot.currency_id == currency_id, CurrencyLot.remaining_quantity < 0
        )
        .order_by(CurrencyLot.created_at)
    )

    to_cover = total_deficit
    for lot in negative_lots:
        if to_cover <= 0:
            break
        fix = min(abs(lot.remaining_quantity), to_cover)
        lot.remaining_quantity += fix
        db.add(lot)
        to_cover -= fix

    db.commit()
    db.refresh(new_lot)

    # ✅ 5. بث إشعار
    await manager.broadcast(
        {
            "type": "currency_lot_added",
            "content": (
                f"📦 تم إضافة دفعة جديدة للعملة {currency.name}: "
                f"الكمية {lot_data.quantity} وحدة - المخزون الجديد {adjusted_remaining} وحدة"
            ),
        }
    )

    return new_lot


@router.post("/add/{currency_id}/lots", response_model=CurrencyLotOut)
def add_currency_lot(
    currency_id: int,
    data: CurrencyLotCreate,
    db: Session = Depends(get_db),
):
    # 1) create the CurrencyLot as you do today
    lot = CurrencyLot(
        currency_id=currency_id,
        quantity=data.quantity,
        remaining_quantity=data.quantity,
        cost_per_unit=data.cost_per_unit,
    )
    db.add(lot)
    db.flush()  # so lot.id gets populated

    # 2) now record the audit log
    log = CurrencyLotLog(
        lot_id=lot.id,
        currency_id=currency_id,
        quantity_added=data.quantity,
        cost_per_unit=data.cost_per_unit,
    )
    db.add(log)

    db.commit()
    db.refresh(lot)
    return lot


@router.get("/{currency_id}/lots/logs", response_model=List[CurrencyLotLogOut])
def get_currency_lot_logs(
    currency_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(CurrencyLotLog)
        .filter(CurrencyLotLog.currency_id == currency_id)
        .order_by(CurrencyLotLog.created_at.desc())
        .all()
    )
