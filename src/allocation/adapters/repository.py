import abc
from typing import List

from allocation.domain.model import Batch


#############################
#           PORT            #
#############################
class AbstractRepository(abc.ABC):

    @abc.abstractmethod
    def add(self, batch: Batch):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, ref: str) -> Batch:
        raise NotImplementedError

    @abc.abstractmethod
    def list(self) -> list:
        raise NotImplementedError


#############################
#         ADAPTERS          #
#############################
class SQLAlchemyRepository(AbstractRepository):

    def __init__(self, session):
        self.session = session

    def add(self, batch: Batch):
        self.session.add(batch)

    def get(self, ref: str) -> Batch:
        return self.session.query(Batch).filter_by(ref=ref).one()

    def list(self) -> List[Batch]:
        return self.session.query(Batch).all()


class FakeRepository(AbstractRepository):

    def __init__(self, batches: set[Batch]):
        self._batches = set(batches)

    def add(self, batch: Batch):
        self._batches.add(batch)

    def get(self, ref: str) -> Batch:
        return next(b for b in self._batches if b.ref == ref)

    def list(self):
        return list(self._batches)