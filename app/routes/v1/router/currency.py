from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.currency import Currency
from app.models.currency_lot import CurrencyLot
from app.schemas.currency_lot import CurrencyLotOut, CurrencyLotCreate
from app.schemas.currency import CurrencyCreate, CurrencyUpdate, CurrencyOut
from app.dependencies import get_db
from app.core.security import require_admin

router = APIRouter()


@router.get("/currencies/get", response_model=List[CurrencyOut])
def get_all_currencies(db: Session = Depends(get_db)):
    return db.query(Currency).all()


@router.post("/currencies/create", response_model=CurrencyOut, dependencies=[Depends(require_admin)])
def create_currency(data: CurrencyCreate, db: Session = Depends(get_db)):
    currency = Currency(**data.dict())
    db.add(currency)
    db.commit()
    db.refresh(currency)
    return currency


@router.put("/currencies/{currency_id}", response_model=CurrencyOut, dependencies=[Depends(require_admin)])
def update_currency(currency_id: int, data: CurrencyUpdate, db: Session = Depends(get_db)):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(currency, field, value)

    db.commit()
    db.refresh(currency)
    return currency


@router.post(
    "/currencies/{currency_id}/lots",
    response_model=CurrencyLotOut,
    dependencies=[Depends(require_admin)],
)
def add_currency_lot(
    currency_id: int,
    data: CurrencyLotCreate, 
    db: Session = Depends(get_db),
):
    currency = db.query(Currency).get(currency_id)
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")

    lot = CurrencyLot(
        currency_id=currency_id,
        quantity=data.quantity,
        remaining_quantity=data.quantity,
        cost_per_unit=data.cost_per_unit,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot
