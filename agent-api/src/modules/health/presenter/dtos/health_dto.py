from pydantic import BaseModel


class HealthCheckResponseDto(BaseModel):
    status: str
