from fastapi import APIRouter, Request

from src.configs import config
from src.libs.rate_limit import limiter
from src.modules.auth.presenter.dependencies import CurrentUserDep
from src.modules.auth.presenter.dtos import LoginRequestDto, LoginResponseDto, MeResponseDto
from src.modules.auth.usecases import LoginUsecaseDep

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
me_router = APIRouter(prefix="/api/v1", tags=["auth"])


@auth_router.post("/login", response_model=LoginResponseDto)
@limiter.limit(config.rate_limit_login)
async def login(request: Request, body: LoginRequestDto, usecase: LoginUsecaseDep) -> LoginResponseDto:
    issued = await usecase.execute(body.email, body.password)
    return LoginResponseDto(access_token=issued.access_token, expires_in=issued.expires_in)


@me_router.get("/me", response_model=MeResponseDto)
async def get_me(user: CurrentUserDep) -> MeResponseDto:
    return MeResponseDto.from_entity(user)
