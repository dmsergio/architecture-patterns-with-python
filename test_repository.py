from model import Batch, Orderline
from repository import SQLAlchemyRepository


def test_repository_can_save_a_batch(session):
    batch = Batch("The batch", "SKU-0101", 100)

    SQLAlchemyRepository(session).add(batch)
    session.commit()

    expected = [("The batch", "SKU-0101", 100)]
    rows = list(
        session.execute("SELECT reference, sku, _purchased_qty FROM batches"))
    assert rows == expected


def insert_order_line(session):
    session.execute(
        "INSERT INTO order_lines (orderid, sku, qty)"
        " VALUES ('order1', 'GENERIC-SOFA', 12)"
    )
    [[order_line_id]] = session.execute(
        "SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku",
        dict(orderid="order1", sku="GENERIC-SOFA"),
    )
    return order_line_id


def insert_batch(session, batch_id):
    session.execute(
        "INSERT INTO batches (reference, sku, _purchased_qty, eta) "
        "VALUES (:batch_id, 'GENERIC-SOFA', 100, null)",
        dict(batch_id=batch_id),
    )
    [[batch_id]] = session.execute(
        "SELECT id FROM batches"
        "WHERE reference=:batch_id AND sku='GENERIC-SOFA'",
        dict(batch_id=batch_id),
    )
    return batch_id


def insert_allocation(session, order_line_id, batch_id):
    session.execute(
        "INSERT INTO allocations (order_line_id, batch_id) "
        "VALUES (:order_line_id, :batch_id)",
        dict(order_line_id=order_line_id, batch_id=batch_id),
    )


def test_repository_can_retrieve_a_batch_with_allocations(session):
    order_line_id = insert_order_line(session)
    batch1_id = insert_batch(session, "batch1")
    insert_batch(session, "batch2")
    insert_allocation(session, order_line_id, batch1_id)

    repo = SQLAlchemyRepository(session)
    retrieved = repo.get("batch1")

    expected = Batch("batch1", "GENERIC-SOFA", 100, eta=None)
    assert retrieved == expected  # Batch.__eq__ only compares reference
    assert retrieved.sku == expected.sku
    assert retrieved._purchased_qty == expected._purchased_qty
    assert retrieved._allocations == {
        Orderline("order1", "GENERIC-SOFA", 12),
    }
