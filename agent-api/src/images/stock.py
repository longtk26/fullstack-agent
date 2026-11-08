"""Stock photos in drafts (Epic 27, Story 27.2): a site's `photo` assets and an app's seeded image fields become
Unsplash photos with their credits. One search per distinct phrase (cached), one after another (the hourly limit is
small), a photo used once per project, its download tracked once. Out of requests or no result: the asset stays a
placeholder (sites) or the field keeps its value (apps), with a note saying why."""

from typing import Any

from .unsplash import StockPhoto, StockUnavailable, UnsplashPhotos, orientation, size_for


def _note(path: str, message: str) -> dict[str, Any]:
    return {"spec": "frontend", "path": path, "message": message, "suggestion": None}


async def _use(photos: UnsplashPhotos, phrase: str, shape: str, used: set[str]) -> StockPhoto:
    photo = await photos.find(phrase, shape, used)
    used.add(photo.id)
    await photos.track(photo)
    return photo


async def stock_site_photos(assets: list[dict[str, Any]], photos: UnsplashPhotos) -> list[dict[str, Any]]:
    """Each `photo` asset (in place): its source becomes the sized Unsplash URL and it gains `credit`. Returns notes."""
    used = {str((a.get("credit") or {}).get("photoId")) for a in assets if isinstance(a.get("credit"), dict)}
    found, missed = [], []
    for asset in assets:
        if asset.get("source") != "photo":
            continue
        ratio = asset.get("aspectRatio") or "16:9"
        phrase = str(asset.get("prompt") or asset.get("alt") or asset["id"].replace("-", " "))
        try:
            photo = await _use(photos, phrase, orientation(ratio), used)
        except StockUnavailable as exc:
            missed.append(f"{asset['id']} ({exc.reason})")
            continue
        asset["source"] = photo.url(*size_for(ratio))
        asset["credit"] = photo.credit(photos.app_name)
        asset.setdefault("alt", photo.alt or phrase)
        found.append(asset["id"])
    notes = []
    if found:
        notes.append(_note("/assets", f"Unsplash photos, credited on the page: {', '.join(found)}"))
    if missed:
        notes.append(_note("/assets", f"No Unsplash photo, shown as placeholders: {'; '.join(missed)}"))
    return notes


def _label(record: dict[str, Any], fields: list[str]) -> str:
    for name in ("name", "title", "label", *fields):
        value = record.get(name)
        if isinstance(value, str) and value.strip() and not value.startswith(("http", "/")):
            return value.strip()
    return ""


async def stock_seed_photos(
    backend: dict[str, Any], photos: UnsplashPhotos, limit: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """An app's seeded records with image fields (in place, at most `limit` photos): each value becomes an Unsplash
    photo found from the record's label and its entity ("Pain de Campagne bread"). Returns the photos as FrontendSpec
    assets (their credits, for the kit) and notes."""
    images = {
        entity["name"]: [field["name"] for field in entity.get("fields") or [] if field.get("type") == "image"]
        for entity in backend.get("entities") or []
    }
    texts = {
        entity["name"]: [f["name"] for f in entity.get("fields") or [] if f.get("type") in ("string", "text")]
        for entity in backend.get("entities") or []
    }
    used: set[str] = set()
    assets: list[dict[str, Any]] = []
    found, missed = 0, []
    for seed in backend.get("seed") or []:
        entity = seed.get("entity")
        for field in images.get(entity) or []:
            for record in seed.get("records") or []:
                if found >= limit:
                    break
                label = _label(record, texts.get(entity) or [])
                phrase = f"{label} {entity}".strip() if label else str(entity)
                try:
                    photo = await _use(photos, phrase, "landscape", used)
                except StockUnavailable as exc:
                    missed.append(f"{entity}.{field} '{label or entity}' ({exc.reason})")
                    continue
                url = photo.url(1200, 800)
                record[field] = url
                found += 1
                assets.append(
                    {
                        "id": f"seed-{len(assets) + 1}",
                        "kind": "image",
                        "alt": photo.alt or phrase,
                        "source": url,
                        "credit": photo.credit(photos.app_name),
                    }
                )
    notes = []
    if found:
        notes.append(_note("/assets", f"{found} seeded record photo(s) from Unsplash, credited where they show"))
    if missed:
        notes.append(_note("/assets", f"No Unsplash photo for: {'; '.join(missed[:8])}"))
    return assets, notes
