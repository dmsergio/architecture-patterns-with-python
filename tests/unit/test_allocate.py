from datetime import date, timedelta
import pytest

from allocation.domain.model import Batch, Orderline, OutOfStock, Product

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_earlier_batches():
    sku = "SKU-0101"

    earliest = Batch("earliest batch", sku, 50, eta=today)
    medium = Batch("medium batch", sku, 50, eta=tomorrow)
    latest = Batch("latest batch", sku, 50, eta=later)

    product = Product(sku, [earliest, medium, latest])
    product.allocate(Orderline("order 01", sku, 20))

    assert earliest.available_quantity == 30
    assert medium.available_quantity == 50
    assert latest.available_quantity == 50


def test_returns_allocated_batch_ref():
    sku = "SKU-0101"

    earliest = Batch("earliest batch", sku, 50, eta=today)
    medium = Batch("medium batch", sku, 50, eta=tomorrow)
    latest = Batch("latest batch", sku, 50, eta=later)

    product = Product(sku, [earliest, medium, latest])
    allocated_batch_ref = product.allocate(Orderline("order 01", sku, 20))

    assert allocated_batch_ref == "earliest batch"


def test_raises_out_of_stock_exception_if_cannot_allocate():
    sku = "SKU-0101"
    batch = Batch("batch", sku, 100)
    product = Product(sku, [batch])
    product.allocate(Orderline("order 01", sku, 80))

    with pytest.raises(OutOfStock, match=sku):
        product.allocate(Orderline("order 02", sku, 50))
