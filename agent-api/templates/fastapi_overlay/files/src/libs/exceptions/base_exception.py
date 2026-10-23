from http import HTTPStatus
from typing import Any

from fastapi import HTTPException

from .error_codes import ErrorCode


class BaseException(HTTPException):
    """Business error. Rendered as {"error": {"code", "message", "details"}} by the handler in handlers.py."""

    def __init__(self, status_code: int, message: str, code: ErrorCode, details: Any = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "details": details})


class BadRequestException(BaseException):
    def __init__(self, message: str = "Bad request", code: ErrorCode = ErrorCode.BAD_REQUEST, details: Any = None):
        super().__init__(HTTPStatus.BAD_REQUEST, message, code, details)


class UnauthorizedException(BaseException):
    def __init__(self, message: str = "Unauthorized", code: ErrorCode = ErrorCode.UNAUTHORIZED, details: Any = None):
        super().__init__(HTTPStatus.UNAUTHORIZED, message, code, details)


class ForbiddenException(BaseException):
    def __init__(self, message: str = "Forbidden", code: ErrorCode = ErrorCode.FORBIDDEN, details: Any = None):
        super().__init__(HTTPStatus.FORBIDDEN, message, code, details)


class NotFoundException(BaseException):
    def __init__(self, message: str = "Resource not found", code: ErrorCode = ErrorCode.NOT_FOUND, details: Any = None):
        super().__init__(HTTPStatus.NOT_FOUND, message, code, details)


class ConflictException(BaseException):
    def __init__(self, message: str = "Conflict", code: ErrorCode = ErrorCode.CONFLICT, details: Any = None):
        super().__init__(HTTPStatus.CONFLICT, message, code, details)


class InternalServerErrorException(BaseException):
    def __init__(
        self, message: str = "Internal server error", code: ErrorCode = ErrorCode.INTERNAL_ERROR, details: Any = None
    ):
        super().__init__(HTTPStatus.INTERNAL_SERVER_ERROR, message, code, details)
