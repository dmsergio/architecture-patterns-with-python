from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    String,
)
from sqlalchemy.orm import mapper, relationship


from allocation.domain.model import Batch, Orderline


metadata = MetaData()

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
    Column("orderid", String(255)),
)

batches = Table(
    "batches",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ref", String(255)),
    Column("sku", String(255)),
    Column("_purchased_qty", Integer, nullable=False),
    Column("eta", Date, nullable=True),
)

allocations = Table(
    "allocations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("batch_id", ForeignKey("batches.id")),
    Column("order_line_id", ForeignKey("order_lines.id")),
)

def start_mappers():
    lines_mapper = mapper(Orderline, order_lines)
    mapper(
        Batch,
        batches,
        properties={
            "_allocations": relationship(
                lines_mapper, secondary=allocations, collection_class=set
            )
        },
    )
