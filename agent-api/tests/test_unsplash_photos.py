"""Stock photos from Unsplash (Epic 27): a phrase becomes a hotlinked, credited photo; searches are cached, a used photo
is tracked once, and an exhausted hour or an empty search leaves the asset as it was with a reason. The Unsplash API is
httpx's MockTransport here (no network)."""

import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from src.images.stock import stock_seed_photos, stock_site_photos
from src.images.unsplash import StockUnavailable, UnsplashPhotos, orientation, size_for
from src.modules.shared.domain.frontend_spec.schema_v1 import Asset
from src.orchestrator.frontend.asset_registry import assets_ts


def _item(index: int) -> dict:
    return {
        "id": f"photo{index}",
        "width": 4000,
        "height": 3000,
        "color": "#c0a080",
        "alt_description": f"a loaf of bread {index}",
        "urls": {"raw": f"https://images.unsplash.com/photo-{index}?ixid=abc"},
        "links": {
            "html": f"https://unsplash.com/photos/photo{index}",
            "download_location": f"https://api.unsplash.com/photos/photo{index}/download?ixid=abc",
        },
        "user": {"name": f"Ana {index}", "links": {"html": f"https://unsplash.com/@ana{index}"}},
    }


class _Api:
    def __init__(self, results: int = 3, status: int = 200, remaining: int = 49):
        self.calls: list[httpx.Request] = []
        self.results, self.status, self.remaining = results, status, remaining

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        headers = {"x-ratelimit-remaining": str(self.remaining)}
        if self.status != 200:
            return httpx.Response(self.status, text="Rate Limit Exceeded", headers=headers)
        if request.url.path == "/search/photos":
            return httpx.Response(
                200, json={"results": [_item(i) for i in range(1, self.results + 1)]}, headers=headers
            )
        return httpx.Response(200, json={"url": "https://images.unsplash.com/x"}, headers=headers)

    @property
    def searches(self) -> list[httpx.Request]:
        return [call for call in self.calls if call.url.path == "/search/photos"]

    @property
    def downloads(self) -> list[httpx.Request]:
        return [call for call in self.calls if call.url.path.endswith("/download")]


def _photos(tmp_path, api: _Api) -> UnsplashPhotos:
    return UnsplashPhotos("key-1", "bga_test", tmp_path / "stock", transport=httpx.MockTransport(api))


def test_a_phrase_becomes_a_hotlinked_photo_with_its_credit(tmp_path):
    api = _Api()
    photo = asyncio.run(_photos(tmp_path, api).find("sourdough loaf", "landscape"))
    request = api.searches[0]
    assert request.headers["Authorization"] == "Client-ID key-1" and request.headers["Accept-Version"] == "v1"
    query = parse_qs(request.url.query.decode())
    assert query["query"] == ["sourdough loaf"] and query["orientation"] == ["landscape"]
    assert query["content_filter"] == ["high"]
    url = urlparse(photo.url(1600, 900))
    assert url.netloc == "images.unsplash.com", "hotlinked, never re-hosted"
    sized = parse_qs(url.query)
    assert {key: sized[key] for key in ("w", "h", "fit", "ixid")} == {
        "w": ["1600"], "h": ["900"], "fit": ["crop"], "ixid": ["abc"]
    }  # fmt: skip
    credit = photo.credit("bga_test")
    assert credit["name"] == "Ana 1"
    assert credit["profileUrl"] == "https://unsplash.com/@ana1?utm_source=bga_test&utm_medium=referral"
    assert credit["sourceUrl"] == "https://unsplash.com/?utm_source=bga_test&utm_medium=referral"


def test_a_repeated_phrase_costs_no_request_and_a_used_photo_is_skipped(tmp_path):
    api = _Api()
    photos = _photos(tmp_path, api)
    first = asyncio.run(photos.find("Sourdough  loaf", "landscape"))
    second = asyncio.run(photos.find("sourdough loaf", "landscape", used={first.id}))
    again = asyncio.run(_photos(tmp_path, api).find("sourdough loaf", "landscape"))  # a new instance, the same cache
    assert len(api.searches) == 1 and second.id != first.id and again.id == first.id


def test_a_used_photo_is_tracked_once(tmp_path):
    api = _Api()
    photos = _photos(tmp_path, api)
    photo = asyncio.run(photos.find("bread", "landscape"))
    assert asyncio.run(photos.track(photo)) and asyncio.run(photos.track(photo))
    assert len(api.downloads) == 1 and api.downloads[0].headers["Authorization"] == "Client-ID key-1"


def test_an_exhausted_hour_or_no_result_says_why_and_stops_asking(tmp_path):
    api = _Api(status=403, remaining=0)
    photos = _photos(tmp_path, api)
    with pytest.raises(StockUnavailable, match="out of Unsplash requests"):
        asyncio.run(photos.find("bread", "landscape"))
    with pytest.raises(StockUnavailable, match="out of Unsplash requests"):
        asyncio.run(photos.find("cake", "landscape"))
    assert len(api.calls) == 1, "no request once the hour is used up"
    with pytest.raises(StockUnavailable, match="no Unsplash photo"):
        asyncio.run(_photos(tmp_path / "empty", _Api(results=0)).find("zzqx", "landscape"))


def test_orientation_and_size_follow_the_aspect_ratio():
    assert [orientation(r) for r in ("16:9", "4:5", "1:1", None)] == ["landscape", "portrait", "squarish", "landscape"]
    assert size_for("16:9") == (1600, 900) and size_for("3:4") == (1200, 1600)


def test_a_sites_photo_assets_become_credited_unsplash_photos(tmp_path):
    api = _Api(results=1)
    assets = [
        {"id": "hero", "kind": "image", "alt": "Fresh bread", "source": "photo", "prompt": "bread",
         "aspectRatio": "16:9"},
        {"id": "team", "kind": "image", "alt": "The bakers", "source": "photo", "prompt": "bread"},
        {"id": "logo", "kind": "logo", "source": "generate"},
    ]  # fmt: skip
    notes = asyncio.run(stock_site_photos(assets, _photos(tmp_path, api)))
    hero, team, logo = assets
    assert hero["source"].startswith("https://images.unsplash.com/photo-1") and hero["credit"]["name"] == "Ana 1"
    assert team["source"] == "photo" and "credit" not in team, "the one result is the hero's: a placeholder"
    assert logo["source"] == "generate"
    assert "Unsplash photos, credited on the page: hero" in notes[0]["message"]
    assert "team (no other photo for 'bread')" in notes[1]["message"]
    assert Asset.model_validate(hero).credit.name == "Ana 1", "the FrontendSpec takes the credit"


def test_an_apps_seeded_records_get_photos_from_their_names(tmp_path):
    api = _Api()
    backend = {
        "entities": [{"name": "Product", "fields": [{"name": "id", "type": "uuid"}, {"name": "name", "type": "string"},
                                                    {"name": "photo", "type": "image"}]}],
        "seed": [{"entity": "Product", "records": [
            {"id": "1", "name": "Pain de Campagne", "photo": "/images/products/pain.jpg"},
            {"id": "2", "name": "Croissant", "photo": "/images/products/croissant.jpg"},
            {"id": "3", "name": "Baguette", "photo": None},
        ]}],
    }  # fmt: skip
    assets, notes = asyncio.run(stock_seed_photos(backend, _photos(tmp_path, api), limit=2))
    records = backend["seed"][0]["records"]
    assert records[0]["photo"].startswith("https://images.unsplash.com/") and records[1]["photo"] != records[0]["photo"]
    assert records[2]["photo"] is None, "past the limit: unchanged"
    phrases = [parse_qs(call.url.query.decode())["query"][0] for call in api.searches]
    assert phrases == ["Pain de Campagne Product", "Croissant Product"]
    assert [asset["source"] for asset in assets] == [records[0]["photo"], records[1]["photo"]]
    assert all(asset["credit"]["provider"] == "unsplash" for asset in assets) and "2 seeded" in notes[0]["message"]


def test_the_site_registry_carries_the_credit():
    credit = {"name": "Ana", "profileUrl": "https://unsplash.com/@ana?u=1", "sourceUrl": "https://unsplash.com/?u=1",
              "photoId": "p"}  # fmt: skip
    plan = {"assets": [{"id": "hero", "render": "remote", "url": "https://images.unsplash.com/p?w=1",
                        "aspectRatio": "16:9", "alt": "Bread", "credit": credit}]}  # fmt: skip
    registry = assets_ts(plan)
    entry = registry.split('"hero": ')[1].split("},\n")[0]
    assert 'credit: {"name": "Ana", "profileUrl": "https://unsplash.com/@ana?u=1"' in entry and "photoId" not in entry
    assert "credit?: { name: string; profileUrl: string; sourceUrl: string };" in registry
