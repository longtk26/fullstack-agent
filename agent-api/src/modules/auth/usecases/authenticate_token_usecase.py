import uuid
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import UnauthorizedException
from src.libs.security import decode_access_token
from src.modules.auth.ports.output import IUserRepoDep
from src.modules.shared.domain.entities import UserEntity


class AuthenticateTokenUsecase:
    def __init__(self, user_repo: IUserRepoDep):
        self.user_repo = user_repo

    async def execute(self, token: str | None) -> UserEntity:
        claims = decode_access_token(token) if token else None
        if not claims:
            raise UnauthorizedException("Missing or invalid access token")
        try:
            user_id = uuid.UUID(claims["sub"])
        except ValueError as exc:
            raise UnauthorizedException("Missing or invalid access token") from exc
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise UnauthorizedException("Missing or invalid access token")
        return user


AuthenticateTokenUsecaseDep = Annotated[AuthenticateTokenUsecase, Depends(AuthenticateTokenUsecase)]
