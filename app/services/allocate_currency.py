from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.currency import Currency
from typing import Dict
from app.logger import Logger

logger = Logger.get_logger(__name__)


def allocate_currency_lots(db: Session, currency: Currency, needed_amount: float):
    """
    FIFO allocate up to needed_amount. If you run out of positive stock,
    the remainder is taken (as a negative) from the *newest* lot, letting
    remaining_quantity go negative.
    """
    remaining = needed_amount
    allocations = []

    lots = sorted(currency.lots, key=lambda l: l.created_at)
    for lot in lots:
        if lot.remaining_quantity <= 0:
            continue
        take = min(lot.remaining_quantity, remaining)
        allocations.append((lot, take))
        lot.remaining_quantity -= take
        db.add(lot)
        remaining -= take
        if remaining <= 0:
            break

    if remaining > 0:
        if not lots:
            raise HTTPException(
                status_code=400, detail="No currency lots exist to allocate from"
            )
        newest = lots[-1]
        allocations.append((newest, remaining))
        newest.remaining_quantity -= remaining
        db.add(newest)

    db.flush()
    return allocations


def allocate_and_compute(
    db: Session,
    currency: Currency,
    needed_amount: float,
    sale_rate: float,
    operation: str,
) -> Dict:
    """
    Compute cost and profit from currency lots for a given transaction.
    - If operation is 'multiply': LYD = foreign * sale_rate
    - If operation is 'divide':  LYD = foreign / sale_rate
    """
    allocations = allocate_currency_lots(db, currency, needed_amount)

    breakdown = []
    total_cost = 0.0
    for lot, qty in allocations:
        if operation == "multiply":
            cost = lot.cost_per_unit * qty
        elif operation == "divide":
            cost = qty / lot.cost_per_unit
        elif operation == "pluse":
            cost = qty
        breakdown.append(
            {
                "lot_id": lot.id,
                "unit_cost": lot.cost_per_unit,
                "quantity": qty,
                "cost": round(cost, 2),
            }
        )
        logger.info(
            "Allocated %s from lot %s (remaining: %s)",
            qty,
            lot.id,
            lot.remaining_quantity,
        )
        logger.info("Cost for this lot: %s", cost)
        total_cost += cost

    if operation == "multiply":
        total_sale = round(needed_amount * sale_rate, 2)
        profit = round(total_sale - total_cost, 2)
        logger.info("Total sale (multiply): %s", total_sale)
        logger.info("Total profit: %s", profit)
    elif operation == "divide":
        total_sale = round(needed_amount / sale_rate, 2)
        profit = round(total_sale - total_cost, 2)
        logger.info("Total sale (divide): %s", total_sale)
        logger.info("Total profit: %s", profit)
    elif operation == "pluse":
        total_sale = needed_amount
        profit = total_sale - total_cost
        logger.info("Total sale (pluse): %s", total_sale)
        logger.info("Total profit: %s", profit)
    else:
        raise ValueError(f"Unsupported operation: {operation}")

    logger.info("Total profit: %s", profit)

    return {
        "breakdown": breakdown,
        "total_cost": round(total_cost, 2),
        "avg_cost": round(total_cost / needed_amount, 4) if needed_amount else 0.0,
        "total_sale": total_sale,
        "profit": profit,
    }
