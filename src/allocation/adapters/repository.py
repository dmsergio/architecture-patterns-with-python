import abc
from typing import List, Set

from allocation.domain import model


#############################
#           PORT            #
#############################
class AbstractProductRepository(abc.ABC):

    def __init__(self):
        self.seen = set()  # type: Set[model.Product]

    def add(self, product: model.Product):
        self._add(product)
        self.seen.add(product)

    def get(self, sku: str) -> model.Product:
        product = self._get(sku)
        if product:
            self.seen.add(product)
        return product

    def list(self) -> List[model.Product]:
        products = self._list()
        if products:
            self.seen.update(products)
        return products

    @abc.abstractmethod
    def _add(self, product: model.Product):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, sku: str) -> model.Product:
        raise NotImplementedError

    @abc.abstractmethod
    def _list(self) -> List[model.Product]:
        raise NotImplementedError


#############################
#         ADAPTERS          #
#############################
class SQLAlchemyProductRepository(AbstractProductRepository):

    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, product: model.Product):
        self.session.add(product)

    def _get(self, sku: str) -> model.Product:
        return (
            self.session.query(model.Product)
                .filter_by(sku=sku)
                .with_for_update()
                .first()
        )

    def _list(self) -> List[model.Product]:
        return self.session.query(model.Product).all()
