from dataclasses import dataclass
from datetime import date
from typing import Optional, Set


@dataclass(frozen=True)
class Orderline:
    orderid: str
    sku: str
    qty: int

    def __repr__(self):
        return f"<({self.__class__.__name__}): {self.orderid}>"


class Batch:

    def __init__(
            self,
            ref: str,
            sku: str,
            qty: int,
            eta: Optional[date]=None,
    ):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_qty = qty
        self._allocations = set()  # type: Set[Orderline]

    def __repr__(self):
        return f"<({self.__class__.__name__}): {self.reference}>"

    def __gt__(self, other):
        if self.eta is None:
            return False
        elif other.eta is None:
            return False
        return self.eta > other.eta

    def __eq__(self, other):
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self):
        return hash(self.reference)

    def allocate(self, line: Orderline):
        if self.can_allocate(line):
            self._allocations.add(line)

    def deallocate(self, line: Orderline):
        if line in self._allocations:
            self._allocations.remove(line)

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_qty - self.allocated_quantity

    def can_allocate(self, line: Orderline) -> bool:
        return line.sku == self.sku and self.available_quantity >= line.qty
