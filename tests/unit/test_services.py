from datetime import datetime, timedelta
from typing import AnyStr, List

import pytest

from allocation.adapters.repository import AbstractRepository
from allocation.domain.model import Batch
from allocation.service_layer import services, unit_of_work

TODAY = datetime.today()
TOMORROW = TODAY + timedelta(days=1)


class FakeRepository(AbstractRepository):

    def __init__(self, batches: List[Batch]):
        self._batches = set(batches)

    def add(self, batch: Batch):
        self._batches.add(batch)

    def get(self, ref: AnyStr) -> Batch:
        return next(b for b in self._batches if b.ref == ref)

    def list(self):
        return list(self._batches)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):

    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self): ...


class FakeSession:

    committed = False

    def commit(self):
        self.committed = True


def test_add_batch():
    uow = FakeUnitOfWork()
    services.add_batch("b-001", "sku-0101", 100, TODAY, uow)
    assert uow.batches.get("b-001") is not None
    assert uow.committed


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()
    services.add_batch("b-002", "sku-0102", 300, TODAY, uow)
    batch_ref = services.allocate("order-002", "sku-0102", 100, uow)
    assert batch_ref == "b-002"


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("b-003", "sku-0103", 300, TODAY, uow)

    with pytest.raises(services.InvalidSku, match="Invalid sku sku-unknown!"):
        services.allocate("order-003", "sku-unknown", 100, uow)


def test_commits():
    uow = FakeUnitOfWork()
    services.add_batch("b-001", "sku-001", 100, None, uow)
    services.allocate("o-001", "sku-001", 10, uow)
    assert uow.committed
