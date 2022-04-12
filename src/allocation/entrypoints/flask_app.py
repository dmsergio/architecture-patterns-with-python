import logging
from datetime import datetime

from flask import Flask, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from allocation import config
from allocation.domain import model
from allocation.adapters import orm, repository
from allocation.service_layer import services, unit_of_work

_logger = logging.getLogger(__name__)


orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)

@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    services.add_batch(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta,
        unit_of_work.SqlAlchemyUnitOfWork(),
    )
    return "OK", 201

@app.route("/allocate", methods=["POST"])
def allocate():
    try:
        batch_ref = services.allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
            unit_of_work.SqlAlchemyUnitOfWork(),
        )
    except services.InvalidSku as e:
        return {"message": str(e)}, 400
    return {"batch_ref": batch_ref}, 201

@app.route("/get_batches", methods=["GET"])
def get_batches():
    session = get_session()
    repo = repository.SQLAlchemyProductRepository(session)
    batches = services.get_batches(repo)
    return {"batches": batches}, 200
