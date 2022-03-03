import pytest

from allocation.domain import model
from allocation.service_layer import unit_of_work


def insert_batch(session, ref, sku, qty, eta):
    session.execute(
        "INSERT INTO batches (ref, sku, _purchased_qty, eta) "
        "VALUES (:ref, :sku, :qty, :eta)",
        dict(ref=ref, sku=sku, qty=qty, eta=eta),
    )


def get_allocated_batch_ref(session, orderid, sku):
    [[order_line_id]] = session.execute(
        "SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku",
        dict(orderid=orderid, sku=sku),
    )
    [[batch_ref]] = session.execute(
        "SELECT b.ref FROM allocations JOIN batches AS b ON batch_id = b.id "
        "WHERE order_line_id=:order_line_id",
        dict(order_line_id=order_line_id),
    )
    return batch_ref


def test_uow_can_retrieve_a_batch_and_allocate_to_it(session_factory):
    session = session_factory()
    insert_batch(session, "batch1", "sku-001", 100, None)
    session.commit()

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        batch = uow.batches.get(ref="batch1")
        line = model.Orderline("order-01", "sku-001", 40)
        batch.allocate(line)
        uow.commit()

    batch_ref = get_allocated_batch_ref(session, "order-01", "sku-001")
    assert batch_ref == "batch1"


def test_rolls_back_uncommitted_work_by_default(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        insert_batch(uow.session, "batch-01", "sku-001", 100, None)

    new_session = session_factory()
    rows = list(new_session.execute("SELECT * FROM batches"))
    assert rows == []


def test_rolls_back_on_error(session_factory):
    class MyException(Exception): ...

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with pytest.raises(MyException):
        with uow:
            insert_batch(uow.session, "batch-01", "sku-001", 100, None)
            raise MyException()

    new_session = session_factory()
    rows = list(new_session.execute("SELECT * FROM batches"))
    assert rows == []
