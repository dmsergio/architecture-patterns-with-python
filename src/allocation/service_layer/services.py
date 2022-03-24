from __future__ import annotations
from datetime import date
from typing import Optional

from allocation.domain import model
from allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def exists_orderid_in_batch(orderid: str, batch: model.Batch) -> bool:
    return orderid in {line.orderid for line in batch._allocations}


def get_order_line_by_orderid(orderid: str, batch) -> model.Orderline:
    return next(line for line in batch._allocations if line.orderid == orderid)


def add_batch(
        ref: str,
        sku: str,
        qty: int,
        eta: Optional[date],
        uow: unit_of_work.AbstractUnitOfWork,
) -> None:
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku, batches=[])
            uow.products.add(product=product)
        product.batches.append(model.Batch(ref, sku, qty, eta))
        uow.commit()


def allocate(
        orderid: str,
        sku: str,
        qty: int,
        uow: unit_of_work.AbstractUnitOfWork,
) -> str:
    line = model.Orderline(orderid, sku, qty)
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {sku}!")
        batch_ref = product.allocate(line)
        uow.commit()
    return batch_ref


# TODO: to use new Product model
# def deallocate(
#         orderid: str,
#         bath_ref: str,
#         uow: unit_of_work.AbstractUnitOfWork,
# ) -> None:
#     with uow:
#         try:
#             batch = uow.batches.get(bath_ref)
#         except NoResultFound:
#             raise InvalidBatch(f"Batch {bath_ref} not found!")
#         if not exists_orderid_in_batch(orderid, batch):
#             raise InvalidOrderidByBatch(f"Order {orderid} not present in batch!")
#         line = get_order_line_by_orderid(orderid, batch)
#         batch.deallocate(line)
#         uow.commit()
