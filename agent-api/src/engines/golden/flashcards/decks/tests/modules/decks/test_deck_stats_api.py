import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_deck_stats_api(client: AsyncClient):
    res = await client.get("/decks")
    assert res.status_code == 200
    decks = res.json()["items"]
    assert len(decks) > 0
    deck_id = decks[0]["id"]

    stats_res = await client.get(f"/decks/{deck_id}/stats")
    assert stats_res.status_code == 200
    data = stats_res.json()
    assert "total" in data
    assert "dueToday" in data
    assert "learned" in data
