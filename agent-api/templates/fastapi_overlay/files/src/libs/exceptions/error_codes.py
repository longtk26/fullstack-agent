from enum import StrEnum


class ErrorCode(StrEnum):
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    REFERENCE_NOT_FOUND = "REFERENCE_NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    # business rules (Story 10.4): a refused state change, an edit of a locked record, a total that does not add up
    INVALID_TRANSITION = "INVALID_TRANSITION"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    TOTAL_MISMATCH = "TOTAL_MISMATCH"
    # uploads (Story 10.5): no object under the key, a type the field does not take, a file too large
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TYPE_NOT_ALLOWED = "FILE_TYPE_NOT_ALLOWED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    # account links (Story 10.7): a password reset or verification token that is wrong, used or expired
    INVALID_TOKEN = "INVALID_TOKEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
