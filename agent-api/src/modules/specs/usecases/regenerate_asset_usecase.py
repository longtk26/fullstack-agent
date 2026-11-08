import asyncio
import hashlib
import io
import tempfile
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends
from PIL import Image

from src.configs import config
from src.configs.config import uploads_dir
from src.images.factory import get_image_generator, get_stock_photos, photos_enabled
from src.images.service import generate_single_photo
from src.images.unsplash import StockUnavailable, UnsplashPhotos, orientation, size_for
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import (
    BadRequestException,
    ConflictException,
    ErrorCode,
    NotFoundException,
    UnprocessableEntityException,
)
from src.libs.ids.ulid import new_upload_id
from src.libs.security import ensure_owner
from src.modules.generations.ports.output import IExecutionRecordRepoDep
from src.modules.shared.domain.entities import UploadEntity, UserEntity
from src.modules.specs.ports.output import ISpecDraftRepoDep
from src.modules.uploads.ports.output import IUploadRepoDep


class RegenerateAssetUsecase:
    def __init__(
        self,
        drafts: ISpecDraftRepoDep,
        uploads: IUploadRepoDep,
        records: IExecutionRecordRepoDep,
    ):
        self.drafts = drafts
        self.uploads = uploads
        self.records = records

    @Transactional
    async def execute(
        self,
        draft_id: uuid.UUID,
        asset_id: str,
        user: UserEntity,
        prompt: str | None = None,
        style: str | None = None,
    ) -> dict[str, Any]:
        draft = self.drafts.find_by_id(draft_id)
        if draft is None:
            raise NotFoundException("Draft not found")
        ensure_owner(draft.owner_id, user.id, user.is_admin, "Draft")
        if not draft.is_terminal:  # the worker still writes it and would overwrite the new photo
            raise ConflictException(
                f"The draft is {str(draft.status).lower()}; regenerate its photos once it has finished",
                code=ErrorCode.CONFLICT,
            )

        if not photos_enabled():
            raise BadRequestException("AI photos are disabled", code=ErrorCode.PHOTOS_DISABLED)

        spec = draft.frontend_spec
        if not isinstance(spec, dict) or not isinstance(spec.get("assets"), list):
            raise NotFoundException(f"Asset '{asset_id}' not found")

        target_asset = None
        for asset in spec["assets"]:
            if isinstance(asset, dict) and asset.get("id") == asset_id:
                target_asset = asset
                break
        if target_asset is None:
            raise NotFoundException(f"Asset '{asset_id}' not found")

        stock = get_stock_photos()
        if stock is not None:  # Epic 27: another Unsplash photo for the phrase (the ones the draft uses are skipped)
            return await self._another_stock_photo(draft, spec, target_asset, stock, prompt)

        generator = get_image_generator()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "photo.webp"
            try:
                async with asyncio.timeout(config.image_timeout_seconds):
                    success, image_call_record, reason = await generate_single_photo(
                        target_asset,
                        temp_path,
                        generator=generator,
                        draft_id=draft.id,
                        custom_prompt=prompt,
                        custom_style=style,
                        use_cache=False,  # a regenerate is a new take, even with the same prompt
                    )
            except TimeoutError as exc:
                raise BadRequestException(
                    f"Photo generation timed out after {config.image_timeout_seconds}s",
                    code=ErrorCode.IMAGE_FAILED,
                ) from exc

            self.records.add_image_calls([image_call_record])

            if not success or not temp_path.is_file():
                err_text = (reason or "") + " " + (image_call_record.error or "")
                if "block" in err_text.lower():
                    raise UnprocessableEntityException(
                        reason or "Photo was blocked by safety filters",
                        code=ErrorCode.IMAGE_BLOCKED,
                    )
                raise BadRequestException(reason or "Photo generation failed", code=ErrorCode.IMAGE_FAILED)

            webp_bytes = temp_path.read_bytes()
            sha256 = hashlib.sha256(webp_bytes).hexdigest()
            existing = self.uploads.find_by_sha256(draft.owner_id, sha256)
            if existing is not None:
                upload_id = existing.id
            else:
                with Image.open(io.BytesIO(webp_bytes)) as im:
                    width, height = im.size

                upload = UploadEntity(
                    id=new_upload_id(),
                    owner_id=draft.owner_id,
                    filename=f"{asset_id}.webp",
                    mime="image/webp",
                    bytes=len(webp_bytes),
                    width=width,
                    height=height,
                    sha256=sha256,
                    origin="photo",
                    prompt=prompt or target_asset.get("prompt"),
                )
                target_file = Path(uploads_dir()) / upload.relative_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_bytes(webp_bytes)
                self.uploads.create(upload)
                upload_id = upload.id

            target_asset["source"] = f"upload:{upload_id}"
            if prompt is not None:
                target_asset["prompt"] = prompt
            if style is not None:
                target_asset["style"] = style

            usage = dict(draft.usage or {})
            draft_calls = self.records.list_draft_image_calls(draft.id)
            img_count = len(draft_calls)
            img_cached = sum(1 for c in draft_calls if c.status == "cached")
            img_cost = round(sum(c.cost_usd for c in draft_calls if c.cost_usd is not None), 6)
            usage["images"] = {"count": img_count, "cached": img_cached, "costUsd": img_cost}
            self.drafts.update(draft.id, frontend_spec=spec, usage=usage)

            return target_asset

    async def _another_stock_photo(
        self,
        draft: Any,
        spec: dict[str, Any],
        asset: dict[str, Any],
        stock: UnsplashPhotos,
        prompt: str | None,
    ) -> dict[str, Any]:
        ratio = asset.get("aspectRatio") or "16:9"
        phrase = prompt or asset.get("prompt") or asset.get("alt") or str(asset.get("id"))
        used = {
            str(item["credit"].get("photoId"))
            for item in spec["assets"]
            if isinstance(item, dict) and isinstance(item.get("credit"), dict)
        }
        try:
            photo = await stock.find(phrase, orientation(ratio), used)
        except StockUnavailable as exc:
            raise BadRequestException(f"No other photo: {exc.reason}", code=ErrorCode.IMAGE_FAILED) from exc
        await stock.track(photo)
        asset["source"] = photo.url(*size_for(ratio))
        asset["credit"] = photo.credit(stock.app_name)
        if prompt is not None:
            asset["prompt"] = prompt
        self.drafts.update(draft.id, frontend_spec=spec)
        return asset


RegenerateAssetUsecaseDep = Annotated[RegenerateAssetUsecase, Depends(RegenerateAssetUsecase)]
