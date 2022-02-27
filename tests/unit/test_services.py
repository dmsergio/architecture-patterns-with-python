from datetime import datetime, timedelta
from typing import AnyStr, List

import pytest

from allocation.adapters.repository import AbstractRepository
from allocation.domain.model import Batch
from allocation.service_layer import services

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


class FakeSession:

    committed = False

    def commit(self):
        self.committed = True


def test_add_batch():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b-001", "sku-0101", 100, TODAY, repo, session)
    assert repo.get("b-001") is not None
    assert session.committed


def test_allocate_returns_allocation():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b-002", "sku-0102", 300, TODAY, repo, session)
    batch_ref = services.allocate("order-002", "sku-0102", 100, repo, session)
    assert batch_ref == "b-002"


def test_allocate_errors_for_invalid_sku():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b-003", "sku-0103", 300, TODAY, repo, session)

    with pytest.raises(services.InvalidSku, match="Invalid sku sku-unknown!"):
        services.allocate("order-003", "sku-unknown", 100, repo, session)


def test_commits():
    repo, session = FakeRepository([]), FakeSession()
    session = FakeSession()
    services.add_batch("b-001", "sku-001", 100, None, repo, session)
    services.allocate("o-001", "sku-001", 10, repo, session)
    assert session.committed is True
