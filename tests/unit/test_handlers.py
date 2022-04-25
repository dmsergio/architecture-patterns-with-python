from datetime import datetime, timedelta
from typing import AnyStr, List
from unittest import mock

import pytest
from allocation.domain import events

from allocation.adapters.repository import AbstractProductRepository
from allocation.domain.model import Product
from allocation.service_layer import unit_of_work, messagebus, handlers

TODAY = datetime.today()
TOMORROW = TODAY + timedelta(days=1)


class FakeProductRepository(AbstractProductRepository):

    def __init__(self, products: List):
        super().__init__()
        self._products = set(products)

    def _add(self, product: Product):
        self._products.add(product)

    def _get(self, sku: AnyStr) -> Product:
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batchref(self, batchref: str) -> Product:
        return next((
            p for p in self._products for b in p.batches
            if b.ref == batchref
        ), None)

    def _list(self) -> List[Product]:
        return list(self._products)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):

    def __init__(self):
        self.products = FakeProductRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self): ...


class FakeUnitOfWorkWithFakeMessageBus(FakeUnitOfWork):
    def __init__(self):
        super().__init__()
        self.events_published = []  # type: List[events.Event]

    def publish_events(self):
        for product in self.products.seen:
            while product.events:
                self.events_published.append(product.events.pop(0))


class FakeSession:

    committed = False

    def commit(self):
        self.committed = True


class TestAddBatch:
    def test_for_new_product(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "sku-001", 100, None), uow)
        assert uow.products.get(sku="sku-001") is not None
        assert uow.committed

    def test_for_existing_product(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "sku-001", 100, None), uow)
        messagebus.handle(events.BatchCreated("b2", "sku-001", 99, None), uow)
        assert "b2" in [b.ref for b in uow.products.get("sku-001").batches]


class TestAllocate:
    def test_returns_allocation(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b2", "sku-001", 100, None), uow)
        results = messagebus.handle(
            events.AllocationRequired("order-01", "sku-001", 10),
            uow,
        )
        assert results.pop(0) == "b2"

    def test_errors_for_invalid_sku(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "sku-001", 300), uow)
        with pytest.raises(handlers.InvalidSku, match="Invalid sku sku-100!"):
            messagebus.handle(
                events.AllocationRequired("order-003", "sku-100", 100),
                uow,
            )

    def test_commits(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "sku-001", 100), uow)
        messagebus.handle(
            events.AllocationRequired("order01", "sku-001", 10),
            uow,
        )
        assert uow.committed

    def test_sends_email_on_out_of_stock_error(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "sku-001", 9, None), uow)

        with mock.patch("allocation.adapters.email.send") as mock_send_mail:
            messagebus.handle(
                events.AllocationRequired("o1", "sku-001", 10), uow
            )
            assert mock_send_mail.call_args == mock.call(
                "stock@made.com",
                f"Out of stock for sku-001",
            )


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "sku-001", 100), uow)
        [batch] = uow.products.get(sku="sku-001").batches
        assert batch.available_quantity == 100

        messagebus.handle(events.BatchQuantityChanged("b1", 50), uow)
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self):
        uow = FakeUnitOfWork()
        event_history = [
            events.BatchCreated("b1", "sku-001", 50),
            events.BatchCreated("b2", "sku-001", 50, TODAY),
            events.AllocationRequired("o1", "sku-001", 20),
            events.AllocationRequired("o2", "sku-001", 20),
        ]
        for event in event_history:
            messagebus.handle(event, uow)
        [batch1, batch2] = uow.products.get(sku="sku-001").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(events.BatchQuantityChanged("b1", 25), uow)

        # order1 or order2 will be deallocated, so we'll have 25-20
        assert batch1.available_quantity == 5
        # and 20 will be reallocated to the next batch
        assert batch2.available_quantity == 30
