# tests/test_allocate_and_compute.py
import pytest
from types import SimpleNamespace

# --- Import the real function under test ---
# adjust the import path to wherever your function lives
from app.services.allocate_currency import allocate_and_compute  # e.g., from app.services.allocate_currency import allocate_and_compute

# We'll monkeypatch allocate_currency_lots via the module where allocate_and_compute references it.
import app.services.allocate_currency as target_module  # same module as above

# Dummy lot object with needed attributes
class DummyLot(SimpleNamespace):
    pass

@pytest.fixture(autouse=True)
def restore_original_allocate(monkeypatch):
    # Ensure we start with the real function; tests will override as needed
    yield
    # No teardown needed if using monkeypatch in tests individually

def test_divide_logic_profit_calculation(monkeypatch):
    """
    divide case:
    - service.price = 10 (means 100 foreign = 10 LYD -> rate = 10/100 = 0.1 -> sale_rate = 1/0.1 = 10)
    - needed_amount = 1000
    - cost per unit = 0.09 => total_cost = 1000 * 0.09 = 90
    - total_sale = 1000 * 10 = 10000
    - profit = 10000 - 90 = 9910
    """
    lot = DummyLot(id=42, cost_per_unit=0.09)

    def fake_allocate_currency_lots(db, currency, needed_amount):
        return [(lot, needed_amount)]

    monkeypatch.setattr(target_module, "allocate_currency_lots", fake_allocate_currency_lots)

    needed_amount = 1000.0
    sale_rate = 1 / (10.0 / 100.0)  # divide logic => 10
    result = allocate_and_compute(db=None, currency=None, needed_amount=needed_amount, sale_rate=sale_rate)

    assert result["total_sale"] == pytest.approx(10000.00)
    assert result["total_cost"] == pytest.approx(90.00)
    assert result["profit"] == pytest.approx(9910.00)
    assert result["avg_cost"] == pytest.approx(0.09, rel=1e-4)
    assert result["breakdown"][0]["lot_id"] == 42
    assert result["breakdown"][0]["quantity"] == needed_amount

def test_multiply_logic_profit_calculation(monkeypatch):
    """
    multiply case:
    - sale_rate = 8 (LYD per foreign)
    - needed_amount = 100
    - cost per unit = 7 => total_cost = 700
    - total_sale = 100 * 8 = 800
    - profit = 100
    """
    lot = DummyLot(id=7, cost_per_unit=7.0)

    def fake_allocate_currency_lots(db, currency, needed_amount):
        return [(lot, needed_amount)]

    monkeypatch.setattr(target_module, "allocate_currency_lots", fake_allocate_currency_lots)

    needed_amount = 100.0
    sale_rate = 8.0
    result = allocate_and_compute(db=None, currency=None, needed_amount=needed_amount, sale_rate=sale_rate)

    assert result["total_sale"] == pytest.approx(800.00)
    assert result["total_cost"] == pytest.approx(700.00)
    assert result["profit"] == pytest.approx(100.00)
    assert result["avg_cost"] == pytest.approx(7.0, rel=1e-4)
    assert result["breakdown"][0]["lot_id"] == 7

def test_zero_needed_amount(monkeypatch):
    """
    Edge case: needed_amount is zero => no allocation, all outputs zero, should not divide by zero.
    """
    def fake_allocate_currency_lots(db, currency, needed_amount):
        return []

    monkeypatch.setattr(target_module, "allocate_currency_lots", fake_allocate_currency_lots)

    needed_amount = 0.0
    sale_rate = 123.45  # irrelevant
    result = allocate_and_compute(db=None, currency=None, needed_amount=needed_amount, sale_rate=sale_rate)

    assert result["total_sale"] == 0.0
    assert result["total_cost"] == 0.0
    assert result["profit"] == 0.0
    assert result["avg_cost"] == 0.0
    assert result["breakdown"] == []
