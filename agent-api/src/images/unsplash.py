"""Stock photos from Unsplash (Epic 27, Story 27.1): a search phrase becomes a real photo and its credit.

Unsplash's API guidelines decide the shape: the photo is hotlinked (its `urls.raw`, sized with `w` / `h` / `fit`), never
downloaded and re-hosted; a used photo is tracked once (`links.download_location`); every photo shows "Photo by <name>
on Unsplash" with links carrying `utm_source=<app>&utm_medium=referral`. Demo applications get 50 requests an hour, so
searches are cached by phrase and orientation (ten results each: another photo for the same phrase costs nothing)
and an exhausted hour stops the searching instead of failing the draft.
"""

import asyncio
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from src.configs import get_logger

logger = get_logger(__name__)

API = "https://api.unsplash.com"
PER_PAGE = 10


class StockUnavailable(Exception):
    """No photo: out of requests this hour, refused (a bad key), no result, or the network."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class StockPhoto:
    id: str
    raw: str  # urls.raw (images.unsplash.com); sized by `url`
    width: int
    height: int
    color: str | None
    alt: str | None
    photographer: str
    profile: str  # the photographer's Unsplash page
    page: str  # the photo's Unsplash page
    download_location: str

    def url(self, width: int, height: int) -> str:
        joiner = "&" if "?" in self.raw else "?"
        return f"{self.raw}{joiner}{urlencode({'w': width, 'h': height, 'fit': 'crop', 'auto': 'format', 'q': 80})}"

    def credit(self, app_name: str) -> dict[str, str]:
        """What a page shows under the photo: "Photo by <name> on Unsplash", both linked with the referral."""
        referral = urlencode({"utm_source": app_name, "utm_medium": "referral"})
        return {
            "provider": "unsplash",
            "name": self.photographer,
            "profileUrl": f"{self.profile}?{referral}",
            "sourceUrl": f"https://unsplash.com/?{referral}",
            "photoId": self.id,
        }


def orientation(aspect_ratio: str | None) -> str:
    """Unsplash's orientation for an asset's aspect ratio ("16:9" → landscape, "4:5" → portrait, "1:1" → squarish)."""
    try:
        width, height = (float(part) for part in str(aspect_ratio or "16:9").split(":", 1))
    except ValueError:
        return "landscape"
    if width > height * 1.1:
        return "landscape"
    if height > width * 1.1:
        return "portrait"
    return "squarish"


def size_for(aspect_ratio: str | None, longest: int = 1600) -> tuple[int, int]:
    try:
        width, height = (float(part) for part in str(aspect_ratio or "16:9").split(":", 1))
    except ValueError:
        width, height = 16.0, 9.0
    if width >= height:
        return longest, max(1, round(longest * height / width))
    return max(1, round(longest * width / height)), longest


def _photo(item: dict[str, Any]) -> StockPhoto | None:
    try:
        user = item["user"]
        return StockPhoto(
            id=str(item["id"]),
            raw=str(item["urls"]["raw"]),
            width=int(item.get("width") or 0),
            height=int(item.get("height") or 0),
            color=item.get("color"),
            alt=item.get("alt_description") or item.get("description"),
            photographer=str(user.get("name") or user.get("username") or "Unknown"),
            profile=str(user["links"]["html"]),
            page=str(item["links"]["html"]),
            download_location=str(item["links"]["download_location"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


class UnsplashPhotos:
    """Search with a cache (`<cache_dir>/unsplash.json`), the hourly limit and download tracking once per photo."""

    def __init__(
        self,
        access_key: str,
        app_name: str,
        cache_dir: Path,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 20.0,
    ):
        self._headers = {"Authorization": f"Client-ID {access_key}", "Accept-Version": "v1"}
        self.app_name = app_name
        self._cache_file = cache_dir / "unsplash.json"
        self._transport = transport
        self._timeout = timeout
        self._lock = asyncio.Lock()
        self.requests = 0  # made by this instance (searches and tracking)
        self.remaining: int | None = None  # the hour's requests left, from the last answer
        self.exhausted_reason: str | None = None

    # -- cache ------------------------------------------------------------------------------------------------------

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self._cache_file.read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._cache_file.parent, prefix=".unsplash.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(data, handle)
            os.replace(tmp, self._cache_file)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    @staticmethod
    def _key(phrase: str, shape: str) -> str:
        return f"{shape}|{' '.join(phrase.lower().split())}"

    # -- the API ----------------------------------------------------------------------------------------------------

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        if self.exhausted_reason:
            raise StockUnavailable(self.exhausted_reason)
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout) as client:
                response = await client.get(url, params=params, headers=self._headers)
        except httpx.HTTPError as exc:
            raise StockUnavailable(f"Unsplash could not be reached ({type(exc).__name__})") from exc
        self.requests += 1
        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining is not None and remaining.isdigit():
            self.remaining = int(remaining)
        if response.status_code == 403 or (response.status_code == 429):
            self.exhausted_reason = "out of Unsplash requests this hour"
            raise StockUnavailable(self.exhausted_reason)
        if response.status_code == 401:
            self.exhausted_reason = "Unsplash refused the access key (401)"
            raise StockUnavailable(self.exhausted_reason)
        if response.status_code >= 400:
            raise StockUnavailable(f"Unsplash answered {response.status_code}")
        if self.remaining == 0:
            self.exhausted_reason = "out of Unsplash requests this hour"
        return response

    async def find(self, phrase: str, shape: str, used: set[str] | None = None) -> StockPhoto:
        """The first result for the phrase not already `used` in the project (photo ids); cached searches cost no
        request."""
        phrase = " ".join(phrase.split())[:100]
        if not phrase:
            raise StockUnavailable("no search phrase")
        used = used or set()
        key = self._key(phrase, shape)
        async with self._lock:
            results = self._read().get("searches", {}).get(key)
        if results is None:
            params = {"query": phrase, "orientation": shape, "per_page": PER_PAGE, "content_filter": "high"}
            response = await self._get(f"{API}/search/photos", params)
            try:
                items = response.json().get("results") or []
            except ValueError as exc:
                raise StockUnavailable("Unsplash answered something that is not JSON") from exc
            results = [asdict(photo) for photo in map(_photo, items) if photo is not None]
            async with self._lock:
                data = self._read()
                data.setdefault("searches", {})[key] = results
                self._write(data)
        for item in results:
            if item["id"] not in used:
                return StockPhoto(**item)
        raise StockUnavailable(f"no Unsplash photo for '{phrase}'" if not results else f"no other photo for '{phrase}'")

    async def track(self, photo: StockPhoto) -> bool:
        """Unsplash's download tracking, once per photo (the cache remembers it); False when it could not be sent."""
        async with self._lock:
            if photo.id in set(self._read().get("tracked") or []):
                return True
        try:
            await self._get(photo.download_location)
        except StockUnavailable as exc:
            logger.warning("unsplash download tracking not sent", extra={"photo": photo.id, "reason": exc.reason})
            return False
        async with self._lock:
            data = self._read()
            data["tracked"] = sorted({*(data.get("tracked") or []), photo.id})
            self._write(data)
        return True
