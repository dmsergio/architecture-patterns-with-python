import abc

from model import Batch


class AbstractRepository(abc.ABC):

    @abc.abstractmethod
    def add(self, batch: Batch):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference: str) -> Batch:
        raise NotImplementedError
