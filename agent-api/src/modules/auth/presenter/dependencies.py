from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.configs import config
from src.libs.exceptions import ForbiddenException
from src.modules.auth.usecases import AuthenticateTokenUsecaseDep
from src.modules.shared.domain.entities import UserEntity

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    usecase: AuthenticateTokenUsecaseDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserEntity:
    # The cookie fallback serves EventSource (SSE) requests, which cannot set headers.
    token = credentials.credentials if credentials else request.cookies.get(config.auth_cookie_name)
    return await usecase.execute(token)


CurrentUserDep = Annotated[UserEntity, Depends(get_current_user)]


async def get_admin_user(user: CurrentUserDep) -> UserEntity:
    if not user.is_admin:
        raise ForbiddenException("Admin role required")
    return user


AdminUserDep = Annotated[UserEntity, Depends(get_admin_user)]
