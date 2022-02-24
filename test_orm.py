from model import Orderline


def test_orderline_mapper_can_load_lines(session):
    session.execute(
        "INSERT INTO order_lines (orderid, sku, qty) VALUES "
        "('order1', 'SKU-001', 12),"
        "('order2', 'SKU-001', 10),"
        "('order3', 'SKU-001', 20)"
    )
    expected = [
        Orderline("order1", "SKU-001", 12),
        Orderline("order2", "SKU-001", 10),
        Orderline("order3", "SKU-001", 20),
    ]
    assert session.query(Orderline).all() == expected


def test_order_line_mapper_can_dave_lines(session):
    new_line = Orderline("order1", "SKU-001", 12)
    session.add(new_line)
    session.commit()

    rows = list(session.execute("SELECT orderid, sku, qty FROM order_lines"))
    assert rows == [("order1", "SKU-001", 12)]
