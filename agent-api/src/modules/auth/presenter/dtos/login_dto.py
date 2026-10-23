from pydantic import Field

from src.libs.dtos import CamelModel


class LoginRequestDto(CamelModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=1, max_length=256)


class LoginResponseDto(CamelModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
