from datetime import date, timedelta

from model import Batch, Orderline

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


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
