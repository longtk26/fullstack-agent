from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .base_exception import BaseException
from .error_codes import ErrorCode


def error_response(status_code: int, code: str, message: str, details: Any = None, headers=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": jsonable_encoder(details)}}
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def _handle_base_exception(_: Request, exc: BaseException) -> JSONResponse:
    return error_response(exc.status_code, exc.code, str(exc.detail), exc.details, exc.headers)


async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        HTTPStatus.UNPROCESSABLE_ENTITY, ErrorCode.VALIDATION_ERROR, "Request validation failed", exc.errors()
    )


async def _handle_rate_limit(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return error_response(HTTPStatus.TOO_MANY_REQUESTS, ErrorCode.RATE_LIMITED, f"Rate limit exceeded: {exc.detail}")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BaseException, _handle_base_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)
