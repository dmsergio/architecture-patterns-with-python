from datetime import datetime
from unittest import mock

import pytest
from sqlalchemy.orm import clear_mappers

from allocation import views, bootstrap
from allocation.domain import commands

from allocation.service_layer import unit_of_work

TODAY = datetime.today()


@pytest.fixture
def sqlite_bus(sqlite_session_factory):
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=mock.Mock(),
        publish=lambda *args: None,
    )
    yield bus
    clear_mappers()


def test_allocations_view(sqlite_bus):
    sqlite_bus.handle(commands.CreateBatch("batch1", "sku1", 50, None))
    sqlite_bus.handle(commands.CreateBatch("batch2", "sku2", 50, TODAY))
    sqlite_bus.handle(commands.Allocate("order1", "sku1", 20))
    sqlite_bus.handle(commands.Allocate("order1", "sku2", 20))

    # add a spurious batch and order to make sure we're getting the right ones
    sqlite_bus.handle(commands.CreateBatch("batch1-later", "sku1", 50, TODAY))
    sqlite_bus.handle(commands.Allocate("otherorder", "sku1", 30))
    sqlite_bus.handle(commands.Allocate("otherorder", "sku2", 10))

    assert views.allocations("order1", sqlite_bus.uow) == [
        {"sku": "sku1", "batchref": "batch1"},
        {"sku": "sku2", "batchref": "batch2"},
    ]
