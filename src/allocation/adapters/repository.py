import abc
from typing import List

from allocation.domain import model


#############################
#           PORT            #
#############################
class AbstractProductRepository(abc.ABC):

    @abc.abstractmethod
    def add(self, product: model.Product):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, sku: str) -> model.Product:
        raise NotImplementedError

    @abc.abstractmethod
    def list(self) -> List[model.Product]:
        raise NotImplementedError


#############################
#         ADAPTERS          #
#############################
class SQLAlchemyProductRepository(AbstractProductRepository):

    def __init__(self, session):
        self.session = session

    def add(self, product: model.Product):
        self.session.add(product)

    def get(self, sku: str) -> model.Product:
        return (
            self.session.query(model.Product)
                .filter_by(sku=sku)
                .with_for_update()
                .first())

    def list(self) -> List[model.Product]:
        return self.session.query(model.Product).all()
