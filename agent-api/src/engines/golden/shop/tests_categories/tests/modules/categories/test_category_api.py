import os

from sqlalchemy import create_engine
from sqlmodel import Session

from src.modules.shared.infrastructure.models import CategoryModel


def _seed_category(name: str) -> CategoryModel:
    engine = create_engine(os.environ["DB_URL"])
    with Session(engine) as session:
        model = CategoryModel(name=name)
        session.add(model)
        session.commit()
        session.refresh(model)
    engine.dispose()
    return model


def test_list_categories__ok(client):
    _seed_category("Coffee")
    _seed_category("Tea")

    body = client.get("/categories").json()

    assert body["total"] == 2 and body["limit"] == 20 and body["offset"] == 0
    assert {item["name"] for item in body["items"]} == {"Coffee", "Tea"}


def test_list_categories__pagination(client):
    for index in range(5):
        _seed_category(f"Cat {index}")

    page = client.get("/categories", params={"limit": 2, "offset": 2, "sort": "name"}).json()

    assert page["total"] == 5
    assert [item["name"] for item in page["items"]] == ["Cat 2", "Cat 3"]


def test_list_categories__sort(client):
    for name in ("Tea", "Coffee", "Gear"):
        _seed_category(name)

    ascending = client.get("/categories", params={"sort": "name"}).json()["items"]
    descending = client.get("/categories", params={"sort": "-name"}).json()["items"]

    assert [c["name"] for c in ascending] == ["Coffee", "Gear", "Tea"]
    assert [c["name"] for c in descending] == ["Tea", "Gear", "Coffee"]


def test_list_categories__invalid_sort(client):
    assert client.get("/categories", params={"sort": "id"}).status_code == 422
