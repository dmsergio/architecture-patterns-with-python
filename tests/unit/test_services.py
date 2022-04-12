from datetime import datetime, timedelta
from typing import AnyStr, List

import pytest

from allocation.adapters.repository import AbstractProductRepository
from allocation.domain.model import Product
from allocation.service_layer import services, unit_of_work

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

    def _list(self) -> List[Product]:
        return list(self._products)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):

    def __init__(self):
        self.products = FakeProductRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self): ...


class FakeSession:

    committed = False

    def commit(self):
        self.committed = True


def test_add_batch_for_new_product():
    uow = FakeUnitOfWork()
    services.add_batch("b-001", "sku-0101", 100, TODAY, uow)
    assert uow.products.get("sku-0101") is not None
    assert uow.committed


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()
    services.add_batch("b-001", "sku-0001", 100, TODAY, uow)
    services.add_batch("b-002", "sku-0001", 100, TODAY, uow)
    assert "b-002" in {b.ref for b in uow.products.get("sku-0001").batches}


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
