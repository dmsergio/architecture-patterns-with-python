from collections import defaultdict
from datetime import datetime, timedelta
from typing import AnyStr, List, Dict

import pytest

from allocation import bootstrap
from allocation.adapters import notifications
from allocation.adapters.repository import AbstractRepository
from allocation.domain import commands
from allocation.domain.model import Product
from allocation.service_layer import unit_of_work, handlers

TODAY = datetime.today()
TOMORROW = TODAY + timedelta(days=1)


class FakeRepository(AbstractRepository):

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
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self): ...


class FakeNotifications(notifications.AbstractNotifications):
    def __init__(self):
        self.sent = defaultdict(list)  # type: Dict[str, List[str]]

    def send(self, destination, message):
        self.sent[destination].append(message)


def bootstrap_test_app():
    return bootstrap.bootstrap(
        start_orm=False,
        uow=FakeUnitOfWork(),
        notifications=FakeNotifications(),
        publish=lambda *args: None,
    )


class TestAddBatch:
    def test_for_new_product(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "sku-1", 100, None))
        assert bus.uow.products.get(sku="sku-1") is not None
        assert bus.uow.committed

    def test_for_existing_product(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "sku-1", 100, None))
        bus.handle(commands.CreateBatch("b2", "sku-1", 99, None))
        assert "b2" in [b.ref for b in bus.uow.products.get("sku-1").batches]


class TestAllocate:
    def test_allocates(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "sku1", 100, None))
        bus.handle(commands.Allocate("o1", "sku1", 30))
        [batch] = bus.uow.products.get(sku="sku1").batches
        assert batch.available_quantity == 70

    def test_errors_for_invalid_sku(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "sku-001", 300))
        with pytest.raises(handlers.InvalidSku, match="Invalid sku sku-100!"):
            bus.handle(commands.Allocate("order-003", "sku-100", 100))

    def test_commits(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "sku1", 100, None))
        bus.handle(commands.Allocate("o1", "sku1", 10))
        assert bus.uow.committed

    def test_sends_email_on_out_of_stock_error(self):
        fake_notifications = FakeNotifications()
        bus = bootstrap.bootstrap(
            start_orm=False,
            uow=FakeUnitOfWork(),
            notifications=fake_notifications,
            publish=lambda *args: None,
        )
        bus.handle(commands.CreateBatch("b1", "sku-001", 9, None))
        bus.handle(commands.Allocate("o1", "sku-001", 10))
        assert fake_notifications.sent["stock@made.com"] == [
            f"Out of stock for sku-001"
        ]


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "sku-001", 100))
        [batch] = bus.uow.products.get(sku="sku-001").batches
        assert batch.available_quantity == 100

        bus.handle(commands.ChangeBatchQuantity("b1", 50))
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self):
        bus = bootstrap_test_app()
        event_history = [
            commands.CreateBatch("b1", "sku-001", 50),
            commands.CreateBatch("b2", "sku-001", 50, TODAY),
            commands.Allocate("o1", "sku-001", 20),
            commands.Allocate("o2", "sku-001", 20),
        ]
        for event in event_history:
            bus.handle(event)
        [batch1, batch2] = bus.uow.products.get(sku="sku-001").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        bus.handle(commands.ChangeBatchQuantity("b1", 25))

        # order1 or order2 will be deallocated, so we'll have 25-20
        assert batch1.available_quantity == 5
        # and 20 will be reallocated to the next batch
        assert batch2.available_quantity == 30
