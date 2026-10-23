from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from src.libs.exceptions import ErrorCode, UnauthorizedException
from src.libs.security import create_access_token, hash_password, verify_password
from src.modules.auth.ports.output import IUserRepoDep

# Verified against when the email is unknown, so both failure paths cost the same.
_DUMMY_HASH = hash_password("bga-timing-equalizer")


class IssuedToken(BaseModel):
    access_token: str
    expires_in: int


class LoginUsecase:
    def __init__(self, user_repo: IUserRepoDep):
        self.user_repo = user_repo

    async def execute(self, email: str, password: str) -> IssuedToken:
        user = self.user_repo.find_by_email(email)
        password_ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if not user or not password_ok:
            raise UnauthorizedException("Invalid email or password", code=ErrorCode.INVALID_CREDENTIALS)
        token, expires_in = create_access_token(str(user.id), {"role": user.role})
        return IssuedToken(access_token=token, expires_in=expires_in)


LoginUsecaseDep = Annotated[LoginUsecase, Depends(LoginUsecase)]
