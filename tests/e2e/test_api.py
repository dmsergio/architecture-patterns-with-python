import pytest
import requests

from allocation import config
from e2e import api_client
from random_refs import *


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_202_and_batch_is_allocated():
    orderid = random_element("order")
    sku, other_sku = random_element("sku"), random_element("sku", "other")
    early_batch = random_element("batch", "1")
    later_batch = random_element("batch", "2")
    other_batch = random_element("batch", "3")
    api_client.post_to_add_batch(early_batch, sku, 100, "2022-02-27")
    api_client.post_to_add_batch(later_batch, sku, 100, "2022-02-28")
    api_client.post_to_add_batch(other_batch, other_sku, 100, None)

    response = api_client.post_to_allocate(orderid, sku, qty=3)
    assert response.status_code == 202

    response = api_client.get_allocation(orderid)
    assert response.ok
    assert response.json() == [
        {"sku": sku, "batchref": early_batch},
    ]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_add_batch_returns_201():
    sku = random_element("sku")
    batch_1 = random_element("batch", "1")
    batch_2 = random_element("batch", "2")
    batch_3 = random_element("batch", "3")
    api_client.post_to_add_batch(batch_1, sku, 200, "2022-02-27")
    api_client.post_to_add_batch(batch_2, sku, 1000, "2022-02-28")
    api_client.post_to_add_batch(batch_3, sku, 50, None)


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_batch_not_found_if_out_of_stock():
    sku = random_element("sku")
    batch = random_element("batch", "1")
    orderid = random_element("order")
    api_client.post_to_add_batch(batch, sku, 100, "2022-02-27")
    response = api_client.post_to_allocate(orderid, sku, 200)
    assert response.status_code == 202

    response = api_client.get_allocation(orderid)
    assert response.text == "not found"
    assert response.status_code == 404


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
def test_happy_path_returns_202_and_batch_is_allocated():
    orderid = random_element("order")
    sku, other_sku = random_element("sku"), random_element("sku")
    early_batch = random_element("batch1")
    later_batch = random_element("batch2")
    other_batch = random_element("batch3")
    api_client.post_to_add_batch(later_batch, sku, 100, "2011-01-02")
    api_client.post_to_add_batch(early_batch, sku, 100, "2011-01-01")
    api_client.post_to_add_batch(other_batch, sku, 100, None)

    response = api_client.post_to_allocate(orderid, sku, qty=3)
    assert response.status_code == 202

    response = api_client.get_allocation(orderid)
    assert response.ok
    assert response.json() == [{
        "sku": sku,
        "batchref": early_batch
    }]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, orderid = random_element("sku"), random_element("order")
    response = api_client.post_to_allocate(
        orderid, unknown_sku, qty=20, expect_success=False,
    )
    assert response.status_code == 400
    assert response.json()["message"] == f"Invalid sku {unknown_sku}!"

    response = api_client.get_allocation(orderid)
    assert response.status_code == 404
