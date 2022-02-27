import logging
from datetime import datetime

from flask import Flask, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from allocation import config
from allocation.domain import model
from allocation.adapters import orm, repository
from allocation.service_layer import services

_logger = logging.getLogger(__name__)


orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))
app = Flask(__name__)

@app.route("/add_batch", methods=["POST"])
def add_batch():
    session = get_session()
    repo = repository.SQLAlchemyRepository(session)
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    services.add_batch(
        request.json["ref"],
        request.json["sku"],
        request.json["qty"],
        eta,
        repo,
        session,
    )
    return "OK", 201

@app.route("/allocate", methods=["POST"])
def allocate():
    session = get_session()
    repo = repository.SQLAlchemyRepository(session)
    try:
        batch_ref = services.allocate(
            request.json["orderid"],
            request.json["sku"],
            request.json["qty"],
            repo,
            session,
        )
    except (model.OutOfStock, services.InvalidSku) as e:
        return {"message": str(e)}, 400
    return {"batch_ref": batch_ref}, 201

@app.route("/deallocate", methods=["POST"])
def deallocate():
    session = get_session()
    repo = repository.SQLAlchemyRepository(session)
    try:
        services.deallocate(
            request.json["orderid"],
            request.json["batch_ref"],
            repo,
            session,
        )
    except (services.InvalidBatch, services.InvalidOrderidByBatch) as e:
        return {"message": str(e)}, 400
    return "OK", 200

@app.route("/get_batches", methods=["GET"])
def get_batches():
    session = get_session()
    repo = repository.SQLAlchemyRepository(session)
    batches = services.get_batches(repo)
    return {"batches": batches}, 200
