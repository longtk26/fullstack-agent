import uuid
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import NotFoundException
from src.libs.security import ensure_owner
from src.modules.shared.domain.entities import BackendSpecEntity, UserEntity
from src.modules.specs.ports.output import IBackendSpecRepoDep


class GetSpecUsecase:
    def __init__(self, spec_repo: IBackendSpecRepoDep):
        self.spec_repo = spec_repo

    async def execute(self, spec_id: uuid.UUID, user: UserEntity) -> BackendSpecEntity:
        spec = self.spec_repo.find_by_id(spec_id)
        if spec is None:
            raise NotFoundException("BackendSpec not found")
        ensure_owner(spec.owner_id, user.id, user.is_admin, resource="BackendSpec")
        return spec


GetSpecUsecaseDep = Annotated[GetSpecUsecase, Depends(GetSpecUsecase)]
