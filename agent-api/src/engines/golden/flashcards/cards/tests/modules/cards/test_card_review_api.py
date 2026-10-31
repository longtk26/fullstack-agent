import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_card_review_api_updates_sm2(client: AsyncClient):
    res = await client.get("/cards")
    assert res.status_code == 200
    cards = res.json()["items"]
    assert len(cards) > 0
    card_id = cards[0]["id"]
    initial_interval = cards[0]["intervalDays"]

    review_res = await client.post(f"/cards/{card_id}/review", json={"rating": "good"})
    assert review_res.status_code == 200
    updated = review_res.json()
    assert updated["id"] == card_id
    assert updated["intervalDays"] >= initial_interval
    assert updated["repetitionCount"] > 0

    # Also test list due cards
    due_res = await client.get("/cards/due")
    assert due_res.status_code == 200
    assert isinstance(due_res.json(), list)
