from datetime import date, timedelta

from allocation.domain import model, events

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_earlier_batches():
    sku = "SKU-0101"

    earliest = model.Batch("earliest batch", sku, 50, eta=today)
    medium = model.Batch("medium batch", sku, 50, eta=tomorrow)
    latest = model.Batch("latest batch", sku, 50, eta=later)

    product = model.Product(sku, [earliest, medium, latest])
    product.allocate(model.Orderline("order 01", sku, 20))

    assert earliest.available_quantity == 30
    assert medium.available_quantity == 50
    assert latest.available_quantity == 50


def test_returns_allocated_batch_ref():
    sku = "SKU-0101"

    earliest = model.Batch("earliest batch", sku, 50, eta=today)
    medium = model.Batch("medium batch", sku, 50, eta=tomorrow)
    latest = model.Batch("latest batch", sku, 50, eta=later)

    product = model.Product(sku, [earliest, medium, latest])
    allocated_batch_ref = product.allocate(
        model.Orderline("order 01", sku, 20))

    assert allocated_batch_ref == "earliest batch"


def test_records_out_of_stock_event_if_cannot_allocate():
    sku = "SKU-001"
    batch = model.Batch("batch-01", sku, 10, eta=today)
    product = model.Product(sku=sku, batches=[batch])
    product.allocate(model.Orderline("order-01", sku, 10))

    allocation = product.allocate(model.Orderline("order-02", sku, 1))
    assert product.events[-1] == events.OutOfStock(sku)
    assert allocation is None


def test_increments_version_number():
    sku = "sku-01"
    line = model.Orderline("order-01", sku, 10)
    product = model.Product(
        sku=sku, batches=[model.Batch("b1", sku, 100, eta=None)]
    )
    product.version_number = 7
    product.allocate(line)
    assert product.version_number == 8
