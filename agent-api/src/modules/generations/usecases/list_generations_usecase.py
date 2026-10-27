import base64
import json
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from src.libs.exceptions import BadRequestException, ForbiddenException
from src.modules.generations.ports.output import IGenerationRepoDep
from src.modules.shared.domain.entities import GenerationEntity, UserEntity
from src.modules.shared.domain.enums import GenerationStatus
from src.modules.specs.ports.output import IBackendSpecRepoDep, IFrontendSpecRepoDep

from .project_names import project_names


class GenerationListItem(BaseModel):
    generation: GenerationEntity
    project_name: str | None


class GenerationPage(BaseModel):
    items: list[GenerationListItem]
    next_cursor: str | None


def encode_cursor(generation: GenerationEntity) -> str:
    raw = json.dumps([generation.created_at.isoformat(), generation.id])
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        created_at, generation_id = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(created_at), str(generation_id)
    except (ValueError, TypeError) as exc:
        raise BadRequestException("Invalid cursor") from exc


class ListGenerationsUsecase:
    def __init__(
        self,
        generation_repo: IGenerationRepoDep,
        spec_repo: IBackendSpecRepoDep,
        frontend_spec_repo: IFrontendSpecRepoDep,
    ):
        self.generation_repo = generation_repo
        self.spec_repo = spec_repo
        self.frontend_spec_repo = frontend_spec_repo

    async def execute(
        self,
        user: UserEntity,
        status: GenerationStatus | None,
        cursor: str | None,
        limit: int,
        all_owners: bool = False,
    ) -> GenerationPage:
        if all_owners and not user.is_admin:
            raise ForbiddenException("scope=all requires the admin role")
        before = decode_cursor(cursor) if cursor else None
        rows = self.generation_repo.list_page(None if all_owners else user.id, status, before, limit + 1)
        page, has_more = rows[:limit], len(rows) > limit
        names = project_names(page, self.spec_repo, self.frontend_spec_repo)
        return GenerationPage(
            items=[GenerationListItem(generation=row, project_name=names[row.id]) for row in page],
            next_cursor=encode_cursor(page[-1]) if has_more else None,
        )


ListGenerationsUsecaseDep = Annotated[ListGenerationsUsecase, Depends(ListGenerationsUsecase)]
