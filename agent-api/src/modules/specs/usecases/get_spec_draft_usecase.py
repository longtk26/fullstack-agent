import uuid
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import NotFoundException
from src.libs.security import ensure_owner
from src.modules.shared.domain.entities import SpecDraftEntity, UserEntity
from src.modules.specs.ports.output import ISpecDraftRepoDep


class GetSpecDraftUsecase:
    def __init__(self, drafts: ISpecDraftRepoDep):
        self.drafts = drafts

    async def execute(self, draft_id: uuid.UUID, user: UserEntity) -> SpecDraftEntity:
        draft = self.drafts.find_by_id(draft_id)
        if draft is None:
            raise NotFoundException("Draft not found")
        ensure_owner(draft.owner_id, user.id, user.is_admin, "Draft")
        return draft


GetSpecDraftUsecaseDep = Annotated[GetSpecDraftUsecase, Depends(GetSpecDraftUsecase)]
