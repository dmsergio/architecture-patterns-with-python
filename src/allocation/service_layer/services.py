from __future__ import annotations
from datetime import date
from typing import List, Optional

from allocation.domain import model
from allocation.domain.model import Orderline
from allocation.adapters.repository import AbstractRepository


class InvalidSku(Exception):
    pass


class InvalidBatch(Exception):
    pass


class InvalidOrderidByBatch(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def get_batches(repo) -> List[dict]:
    return [dict(ref=batch.ref, sku=batch.sku, qty=batch._purchased_qty)
            for batch in repo.list()]


def exists_orderid_in_batch(orderid, batch):
    return orderid in {line.orderid for line in batch._allocations}


def add_batch(
        ref: str,
        sku: str,
        qty: int,
        eta: Optional[date],
        repo: AbstractRepository,
        session,
) -> None:
    repo.add(model.Batch(ref, sku, qty, eta))
    session.commit()


def allocate(
        order_id: str,
        sku: str,
        qty: int,
        repo: AbstractRepository,
        session,
) -> str:
    batches = repo.list()
    if not is_valid_sku(sku, batches):
        raise InvalidSku(f"Invalid sku {sku}!")
    line = Orderline(order_id, sku, qty)
    batch_ref = model.allocate(line, batches)
    session.commit()
    return batch_ref


def deallocate(
        orderid: str,
        sku: str,
        qty: int,
        bath_ref: str,
        repo: AbstractRepository,
        session,
) -> None:
    batch = repo.get(bath_ref)
    if not batch:
        raise InvalidBatch(f"Batch {bath_ref} not found!")
    if not exists_orderid_in_batch(orderid, batch):
        raise InvalidOrderidByBatch(f"Order {orderid} not present in batch!")
    batch.deallocate(Orderline(orderid, sku, qty))
    session.commit()
