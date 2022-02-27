from datetime import date, timedelta
import pytest

from allocation.domain.model import Batch, Orderline, OutOfStock, allocate

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


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


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = Batch("batch", "SKU-0101", 100)
    allocate(Orderline("order 01", "SKU-0101", 80), [batch])

    with pytest.raises(OutOfStock, match="SKU-0101"):
        allocate(Orderline("order 02", "SKU-0101", 50), [batch])
