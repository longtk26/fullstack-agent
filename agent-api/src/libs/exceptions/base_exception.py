from http import HTTPStatus
from typing import Any

from fastapi import HTTPException

from .error_codes import ErrorCode


class BaseException(HTTPException):
    def __init__(self, status_code: int, detail: Any, code: ErrorCode = ErrorCode.BAD_REQUEST, details: Any = None):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
        self.details = details


class NotFoundException(BaseException):
    def __init__(self, detail: Any = "Resource not found", code: ErrorCode = ErrorCode.NOT_FOUND, details: Any = None):
        super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=detail, code=code, details=details)


class BadRequestException(BaseException):
    def __init__(self, detail: Any = "Bad request", code: ErrorCode = ErrorCode.BAD_REQUEST, details: Any = None):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=detail, code=code, details=details)


class UnauthorizedException(BaseException):
    def __init__(self, detail: Any = "Unauthorized", code: ErrorCode = ErrorCode.UNAUTHORIZED, details: Any = None):
        super().__init__(status_code=HTTPStatus.UNAUTHORIZED, detail=detail, code=code, details=details)
        self.headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenException(BaseException):
    def __init__(self, detail: Any = "Forbidden", code: ErrorCode = ErrorCode.FORBIDDEN, details: Any = None):
        super().__init__(status_code=HTTPStatus.FORBIDDEN, detail=detail, code=code, details=details)


class ConflictException(BaseException):
    def __init__(self, detail: Any = "Conflict", code: ErrorCode = ErrorCode.CONFLICT, details: Any = None):
        super().__init__(status_code=HTTPStatus.CONFLICT, detail=detail, code=code, details=details)


class PayloadTooLargeException(BaseException):
    def __init__(
        self, detail: Any = "Payload too large", code: ErrorCode = ErrorCode.PAYLOAD_TOO_LARGE, details: Any = None
    ):
        super().__init__(status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE, detail=detail, code=code, details=details)


class UnprocessableEntityException(BaseException):
    def __init__(
        self, detail: Any = "Unprocessable entity", code: ErrorCode = ErrorCode.VALIDATION_ERROR, details: Any = None
    ):
        super().__init__(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=detail, code=code, details=details)


class ServiceUnavailableException(BaseException):
    def __init__(
        self, detail: Any = "Service unavailable", code: ErrorCode = ErrorCode.WORKER_UNAVAILABLE, details: Any = None
    ):
        super().__init__(status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail=detail, code=code, details=details)


class InternalServerErrorException(BaseException):
    def __init__(
        self, detail: Any = "Internal server error", code: ErrorCode = ErrorCode.INTERNAL_ERROR, details: Any = None
    ):
        super().__init__(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=detail, code=code, details=details)
