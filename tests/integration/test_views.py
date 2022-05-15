from datetime import datetime

from allocation import views
from allocation.domain import commands

from allocation.service_layer import unit_of_work, messagebus

TODAY = datetime.today()


def test_allocations_view(sqlite_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory)
    messagebus.handle(commands.CreateBatch("batch1", "sku1", 50, None), uow)
    messagebus.handle(commands.CreateBatch("batch2", "sku2", 50, TODAY), uow)
    messagebus.handle(commands.Allocate("order1", "sku1", 20), uow)
    messagebus.handle(commands.Allocate("order1", "sku2", 20), uow)

    # add a spurious batch and order to make sure we're getting the right ones
    messagebus.handle(
        commands.CreateBatch("batch1-later", "sku1", 50, TODAY), uow)
    messagebus.handle(commands.Allocate("otherorder", "sku1", 30), uow)
    messagebus.handle(commands.Allocate("otherorder", "sku2", 10), uow)

    assert views.allocations("order1", uow) == [
        {"sku": "sku1", "batchref": "batch1"},
        {"sku": "sku2", "batchref": "batch2"},
    ]
