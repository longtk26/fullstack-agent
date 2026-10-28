import os
import uuid
from decimal import Decimal

from sqlalchemy import create_engine
from sqlmodel import Session

from src.modules.shared.infrastructure.models import CategoryModel, ProductModel

MISSING = str(uuid.uuid4())


def _seed_category(name: str = "Coffee") -> uuid.UUID:
    engine = create_engine(os.environ["DB_URL"])
    with Session(engine) as session:
        model = CategoryModel(name=name)
        session.add(model)
        session.commit()
        category_id = model.id
    engine.dispose()
    return category_id


def _seed_product(
    category_id: uuid.UUID,
    name: str = "House blend",
    price: float = 9.5,
    description: str | None = "Medium roast",
    stock: int = 40,
) -> ProductModel:
    engine = create_engine(os.environ["DB_URL"])
    with Session(engine) as session:
        model = ProductModel(
            category_id=category_id,
            name=name,
            price=Decimal(str(price)),
            description=description,
            stock=stock,
        )
        session.add(model)
        session.commit()
        session.refresh(model)
    engine.dispose()
    return model


def test_list_products__ok(client):
    category_id = _seed_category()
    _seed_product(category_id, "House blend")
    _seed_product(category_id, "Sencha")

    body = client.get("/products").json()

    assert body["total"] == 2 and body["limit"] == 20 and body["offset"] == 0
    assert {item["name"] for item in body["items"]} == {"House blend", "Sencha"}


def test_list_products__pagination(client):
    category_id = _seed_category()
    for index in range(5):
        _seed_product(category_id, f"P{index}", price=float(index + 1))

    page = client.get("/products", params={"limit": 2, "offset": 1, "sort": "name"}).json()

    assert page["total"] == 5
    assert [item["name"] for item in page["items"]] == ["P1", "P2"]


def test_list_products__filter_category_id(client):
    coffee_id = _seed_category("Coffee")
    tea_id = _seed_category("Tea")
    _seed_product(coffee_id, "Espresso")
    _seed_product(tea_id, "Matcha")

    body = client.get("/products", params={"categoryId": str(coffee_id)}).json()

    assert body["total"] == 1 and body["items"][0]["name"] == "Espresso"


def test_list_products__sort(client):
    category_id = _seed_category()
    _seed_product(category_id, "Cheap", price=5.0)
    _seed_product(category_id, "Premium", price=15.0)

    ascending = client.get("/products", params={"sort": "price"}).json()["items"]
    descending = client.get("/products", params={"sort": "-price"}).json()["items"]

    assert [p["name"] for p in ascending] == ["Cheap", "Premium"]
    assert [p["name"] for p in descending] == ["Premium", "Cheap"]


def test_list_products__invalid_sort(client):
    assert client.get("/products", params={"sort": "stock"}).status_code == 422


def test_list_products__search(client):
    category_id = _seed_category()
    _seed_product(category_id, "House blend", description="Chocolate notes")
    _seed_product(category_id, "Sencha", description="Grassy green tea")

    body = client.get("/products", params={"q": "grassy"}).json()

    assert body["total"] == 1 and body["items"][0]["name"] == "Sencha"


def test_get_product__ok(client):
    category_id = _seed_category()
    product = _seed_product(category_id, "House blend", price=9.5)

    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(product.id) and body["name"] == "House blend" and body["price"] == 9.5


def test_get_product__not_found(client):
    response = client.get(f"/products/{MISSING}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
