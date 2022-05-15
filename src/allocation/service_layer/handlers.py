from __future__ import annotations

from dataclasses import asdict
from typing import List, TYPE_CHECKING

from allocation.adapters import email, redis_eventpublisher
from allocation.domain import model, events, commands


if TYPE_CHECKING:
    from allocation.service_layer import unit_of_work

class InvalidSku(Exception):
    pass


def get_batches(repo) -> List[dict]:
    return [dict(ref=batch.ref, sku=batch.sku, qty=batch._purchased_qty)
            for product in repo.list()
            for batch in product.batches]


def exists_orderid_in_batch(orderid: str, batch: model.Batch) -> bool:
    return orderid in {line.orderid for line in batch._allocations}


def get_order_line_by_orderid(orderid: str, batch) -> model.Orderline:
    return next(line for line in batch._allocations if line.orderid == orderid)


def add_batch(
        cmd: commands.CreateBatch,
        uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    with uow:
        product = uow.products.get(sku=cmd.sku)
        if product is None:
            product = model.Product(cmd.sku, batches=[])
            uow.products.add(product=product)
        product.batches.append(model.Batch(
            cmd.ref,
            cmd.sku,
            cmd.qty,
            cmd.eta,
        ))
        uow.commit()


def allocate(
        cmd: commands.Allocate,
        uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    line = model.Orderline(cmd.orderid, cmd.sku, cmd.qty)
    with uow:
        product = uow.products.get(sku=cmd.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {cmd.sku}!")
        product.allocate(line)
        uow.commit()


def reallocate(
        event: events.Deallocated,
        uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get(sku=event.sku)
        product.events.append(commands.Allocate(**asdict(event)))
        uow.commit()


def change_batch_quantity(
        cmd: commands.ChangeBatchQuantity,
        uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get_by_batchref(batchref=cmd.ref)
        product.change_batch_quantity(ref=cmd.ref, qty=cmd.qty)
        uow.commit()


def send_out_of_stock_notification(
        event: events.OutOfStock,
        uow: unit_of_work.AbstractUnitOfWork,
):
    email.send(
        "stock@made.com",
        f"Out of stock for {event.sku}"
    )


def publish_allocated_event(
        event: events.Allocated,
        uow: unit_of_work.AbstractUnitOfWork,
):
    redis_eventpublisher.publish("line_allocated", event)


def add_allocation_to_read_model(
       event: events.Allocated,
       uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    with uow:
        uow.session.execute(
            """
            INSERT INTO allocations_view (orderid, sku, batchref)
            VALUES (:orderid, :sku, :batchref)
            """,
            dict(
                orderid=event.orderid,
                sku=event.sku,
                batchref=event.batchref,
            )
        )
        uow.commit()


def remove_allocation_from_read_model(
        event: events.Deallocated,
        uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    with uow:
        uow.session.execute(
            """
            DELETE FROM allocations_view
            WHERE orderid = :orderid AND sku = :sku
            """,
            dict(orderid=event.orderid, sku=event.sku),
        )
        uow.commit()
