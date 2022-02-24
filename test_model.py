from datetime import date, timedelta
from typing import List
import pytest

from model import Batch, Orderline

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


# domain service function
def allocate(line: Orderline, batches: List[Batch]) -> str:
    batch = next(batch for batch in sorted(batches)
                 if batch.can_allocate(line))
    batch.allocate(line)
    return batch.reference


def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("Batch 001", sku, batch_qty),
        Orderline("Line 123", sku, line_qty),
    )


def test_allocating_to_a_batch_reduces_the_available_quantity():
    batch, line = make_batch_and_line("SKU-0101", 20, 5)
    batch.allocate(line)
    assert batch.available_quantity == 15


def test_can_allocate_if_available_greater_than_required():
    batch, line = make_batch_and_line("SKU-0101", 20, 10)
    assert batch.can_allocate(line)


def test_cannot_allocate_if_available_smaller_than_required():
    batch, line = make_batch_and_line("SKU-0101", 10, 20)
    assert not batch.can_allocate(line)


def test_can_allocate_if_available_equal_to_required():
    batch, line = make_batch_and_line("SKU-0101", 20, 20)
    assert batch.can_allocate(line)


def test_cannot_allocate_if_skus_don_not_match():
    batch = Batch("Batch 001", "SKU-0101", 20, today)
    line = Orderline("Order 111", "SKU-1234", 5)
    assert not batch.can_allocate(line)


def test_can_only_deallocate_allocated_lines():
    batch, line = make_batch_and_line("SKU-0101", 20, 8)
    batch.deallocate(line)
    assert batch.available_quantity == 20


def test_prefers_current_stock_batches_to_shipments():
    in_stock_batch = Batch("stock batch", "SKU-0101", 50, eta=today)
    shipment_batch = Batch("shipment batch", "SKU-0101", 100, eta=tomorrow)
    line = Orderline("order 01", "SKU-0101", 20)
    allocate(line, [in_stock_batch, shipment_batch])

    assert in_stock_batch.available_quantity == 30
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches():
    earliest = Batch("earliest batch", "SKU-0101", 50, eta=today)
    medium = Batch("medium batch", "SKU-0101", 50, eta=tomorrow)
    latest = Batch("latest batch", "SKU-0101", 50, eta=later)
    line = Orderline("order 01", "SKU-0101", 20)
    allocate(line, [earliest, medium, latest])

    assert earliest.available_quantity == 30
    assert medium.available_quantity == 50
    assert latest.available_quantity == 50


def test_returns_allocated_batch_ref():
    earliest = Batch("earliest batch", "SKU-0101", 50, eta=today)
    medium = Batch("medium batch", "SKU-0101", 50, eta=tomorrow)
    latest = Batch("latest batch", "SKU-0101", 50, eta=later)
    line = Orderline("order 01", "SKU-0101", 20)
    allocated_batch_ref = allocate(line, [earliest, medium, latest])

    assert allocated_batch_ref == "earliest batch"


def test_prefers_warehouse_batches_to_shipments():
    pytest.fail("todo")
