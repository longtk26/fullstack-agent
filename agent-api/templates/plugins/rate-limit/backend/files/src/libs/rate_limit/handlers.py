from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from src.libs.exceptions import ErrorCode
from src.libs.exceptions.handlers import error_response


async def rate_limit_exception_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return error_response(429, ErrorCode.RATE_LIMITED, f"Rate limit exceeded: {exc.detail}")
