import pytest
import requests

from allocation import config
from random_refs import *


def post_to_add_batch(ref, sku, qty, eta=None):
    url = config.get_api_url()
    data = {
        "ref": ref,
        "sku": sku,
        "qty": qty,
        "eta": eta,
    }
    response = requests.post(f"{url}/add_batch", json=data)
    assert response.status_code == 201


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_201_and_allocated_bath():
    sku, other_sku = random_element("sku"), random_element("sku", "other")
    early_batch = random_element("batch", "1")
    later_batch = random_element("batch", "2")
    other_batch = random_element("batch", "3")
    post_to_add_batch(early_batch, sku, 100, "2022-02-27")
    post_to_add_batch(later_batch, sku, 100, "2022-02-28")
    post_to_add_batch(other_batch, other_sku, 100, None)

    data = {
        "orderid": random_element("order"),
        "sku": sku,
        "qty": 5,
    }
    url = config.get_api_url()
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 201
    assert response.json()["batch_ref"] == early_batch


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_add_batch_returns_201():
    sku = random_element("sku")
    batch_1 = random_element("batch", "1")
    batch_2 = random_element("batch", "2")
    batch_3 = random_element("batch", "3")
    post_to_add_batch(batch_1, sku, 200, "2022-02-27")
    post_to_add_batch(batch_2, sku, 1000, "2022-02-28")
    post_to_add_batch(batch_3, sku, 50, None)


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_batch_is_none_if_out_of_stock():
    sku = random_element("sku")
    batch = random_element("batch", "1")
    post_to_add_batch(batch, sku, 100, "2022-02-27")

    data = {
        "orderid": random_element("order"),
        "sku": sku,
        "qty": 200,
    }
    url = config.get_api_url()
    response = requests.post(f"{url}/allocate", json=data)

    assert response.status_code == 201
    assert response.json()["batch_ref"] is None


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_400_message_for_invalid_sku():
    sku = random_element("sku")
    data = dict(
        orderid=random_element("order"),
        sku=sku,
        qty=20,
    )
    url = config.get_api_url()
    response = requests.post(f"{url}/allocate", json=data)
    assert response.status_code == 400
    assert response.json()["message"] == f"Invalid sku {sku}!"


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_get_correct_total_of_batches_after_create_one():
    url = config.get_api_url()
    response = requests.get(f"{url}/get_batches")
    current_batches = len(response.json()["batches"])

    # new batch
    sku = random_element("sku")
    batch = random_element("batch", "1")
    post_to_add_batch(batch, sku, 100)

    response = requests.get(f"{url}/get_batches")
    total_batches = len(response.json()["batches"])
    assert total_batches == current_batches + 1
