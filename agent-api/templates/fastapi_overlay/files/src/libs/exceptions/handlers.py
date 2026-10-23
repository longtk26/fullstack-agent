from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .base_exception import BaseException
from .error_codes import ErrorCode


def _error(status_code: int, code: str, message: str, details: object = None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details}}
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


async def base_exception_handler(_: Request, exc: BaseException) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message, exc.details)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(422, ErrorCode.VALIDATION_ERROR, "Request validation failed", exc.errors())


async def rate_limit_exception_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return _error(429, ErrorCode.RATE_LIMITED, f"Rate limit exceeded: {exc.detail}")
