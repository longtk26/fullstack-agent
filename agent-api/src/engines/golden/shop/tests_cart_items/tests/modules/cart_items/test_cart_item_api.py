import os
import uuid
from decimal import Decimal

from sqlalchemy import create_engine
from sqlmodel import Session

from src.modules.shared.infrastructure.models import CategoryModel, ProductModel

MISSING = str(uuid.uuid4())


def _seed_product(name: str = "House blend") -> str:
    engine = create_engine(os.environ["DB_URL"])
    with Session(engine) as session:
        category = CategoryModel(name=f"Category-{uuid.uuid4()}")
        session.add(category)
        session.flush()
        product = ProductModel(category_id=category.id, name=name, price=Decimal("9.50"), stock=10)
        session.add(product)
        session.commit()
        product_id = str(product.id)
    engine.dispose()
    return product_id


def _create_cart_item(client, product_id: str, quantity: int = 1):
    response = client.post("/cart-items", json={"productId": product_id, "quantity": quantity})
    assert response.status_code == 201, response.text
    return response.json()


def test_list_cart_items__ok(client):
    product_id = _seed_product()
    _create_cart_item(client, product_id, 1)
    _create_cart_item(client, product_id, 2)

    body = client.get("/cart-items").json()

    assert body["total"] == 2 and body["limit"] == 20 and body["offset"] == 0
    assert {item["quantity"] for item in body["items"]} == {1, 2}


def test_list_cart_items__pagination(client):
    product_id = _seed_product()
    for quantity in (1, 2, 3, 4):
        _create_cart_item(client, product_id, quantity)

    page = client.get("/cart-items", params={"limit": 2, "offset": 1, "sort": "createdAt"}).json()

    assert page["total"] == 4
    assert len(page["items"]) == 2


def test_list_cart_items__sort(client):
    product_id = _seed_product()
    first = _create_cart_item(client, product_id, 1)
    second = _create_cart_item(client, product_id, 2)

    ascending = client.get("/cart-items", params={"sort": "createdAt"}).json()["items"]
    descending = client.get("/cart-items", params={"sort": "-createdAt"}).json()["items"]

    assert [i["id"] for i in ascending] == [first["id"], second["id"]]
    assert [i["id"] for i in descending] == [second["id"], first["id"]]


def test_list_cart_items__invalid_sort(client):
    assert client.get("/cart-items", params={"sort": "quantity"}).status_code == 422


def test_create_cart_item__ok(client):
    product_id = _seed_product()

    response = client.post("/cart-items", json={"productId": product_id, "quantity": 3})

    assert response.status_code == 201
    body = response.json()
    assert body["productId"] == product_id and body["quantity"] == 3


def test_create_cart_item__invalid(client):
    product_id = _seed_product()

    assert client.post("/cart-items", json={"productId": product_id, "quantity": 0}).status_code == 422
    assert client.post("/cart-items", json={"productId": product_id, "quantity": 100}).status_code == 422


def test_create_cart_item__bad_reference(client):
    response = client.post("/cart-items", json={"productId": MISSING, "quantity": 1})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "REFERENCE_NOT_FOUND"


def test_update_cart_item__ok(client):
    item = _create_cart_item(client, _seed_product(), 1)

    response = client.patch(f"/cart-items/{item['id']}", json={"quantity": 5})

    assert response.status_code == 200
    assert response.json()["quantity"] == 5


def test_update_cart_item__not_found(client):
    assert client.patch(f"/cart-items/{MISSING}", json={"quantity": 2}).status_code == 404


def test_update_cart_item__invalid(client):
    item = _create_cart_item(client, _seed_product(), 1)

    assert client.patch(f"/cart-items/{item['id']}", json={"quantity": 0}).status_code == 422


def test_delete_cart_item__ok(client):
    item = _create_cart_item(client, _seed_product(), 1)

    assert client.delete(f"/cart-items/{item['id']}").status_code == 204
    assert client.get("/cart-items").json()["total"] == 0


def test_delete_cart_item__not_found(client):
    assert client.delete(f"/cart-items/{MISSING}").status_code == 404
