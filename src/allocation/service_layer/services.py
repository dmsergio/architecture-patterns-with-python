from __future__ import annotations
from datetime import date
from typing import List, Optional

from sqlalchemy.exc import NoResultFound

from allocation.domain import model
from allocation.domain.model import Batch, Orderline
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


def exists_orderid_in_batch(orderid: str, batch: Batch) -> bool:
    return orderid in {line.orderid for line in batch._allocations}


def get_order_line_by_orderid(orderid: str, batch) -> Orderline:
    return next(line for line in batch._allocations if line.orderid == orderid)


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
        orderid: str,
        sku: str,
        qty: int,
        repo: AbstractRepository,
        session,
) -> str:
    batches = repo.list()
    if not is_valid_sku(sku, batches):
        raise InvalidSku(f"Invalid sku {sku}!")
    line = Orderline(orderid, sku, qty)
    batch_ref = model.allocate(line, batches)
    session.commit()
    return batch_ref


def deallocate(
        orderid: str,
        bath_ref: str,
        repo: AbstractRepository,
        session,
) -> None:
    try:
        batch = repo.get(bath_ref)
    except NoResultFound:
        raise InvalidBatch(f"Batch {bath_ref} not found!")
    if not exists_orderid_in_batch(orderid, batch):
        raise InvalidOrderidByBatch(f"Order {orderid} not present in batch!")
    line = get_order_line_by_orderid(orderid, batch)
    batch.deallocate(line)
    session.commit()
