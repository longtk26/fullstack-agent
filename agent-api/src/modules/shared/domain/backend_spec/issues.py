from enum import StrEnum

from pydantic import BaseModel


class SpecIssueCode(StrEnum):
    JSON_MALFORMED = "JSON_MALFORMED"
    SPEC_VERSION_UNSUPPORTED = "SPEC_VERSION_UNSUPPORTED"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    DUPLICATE_ENTITY = "DUPLICATE_ENTITY"
    DUPLICATE_FIELD = "DUPLICATE_FIELD"
    DUPLICATE_OPERATION_ID = "DUPLICATE_OPERATION_ID"
    DUPLICATE_RELATIONSHIP = "DUPLICATE_RELATIONSHIP"
    DUPLICATE_RULE_ID = "DUPLICATE_RULE_ID"
    ROUTE_CONFLICT = "ROUTE_CONFLICT"
    PRIMARY_KEY_MISSING = "PRIMARY_KEY_MISSING"
    PRIMARY_KEY_MULTIPLE = "PRIMARY_KEY_MULTIPLE"
    UNKNOWN_ENTITY_REF = "UNKNOWN_ENTITY_REF"
    UNKNOWN_FIELD_REF = "UNKNOWN_FIELD_REF"
    UNKNOWN_OPERATION_REF = "UNKNOWN_OPERATION_REF"
    UNKNOWN_RULE_REF = "UNKNOWN_RULE_REF"
    TYPE_DEFAULT_MISMATCH = "TYPE_DEFAULT_MISMATCH"
    FOREIGN_KEY_TYPE_MISMATCH = "FOREIGN_KEY_TYPE_MISMATCH"
    ENUM_VALUES_MISSING = "ENUM_VALUES_MISSING"
    AUTH_NOT_CONFIGURED = "AUTH_NOT_CONFIGURED"
    UNKNOWN_POLICY_REF = "UNKNOWN_POLICY_REF"
    UNKNOWN_ROLE_REF = "UNKNOWN_ROLE_REF"
    PATH_PARAM_MISMATCH = "PATH_PARAM_MISMATCH"
    METHOD_ACTION_MISMATCH = "METHOD_ACTION_MISMATCH"
    MANY_TO_MANY_THROUGH_INVALID = "MANY_TO_MANY_THROUGH_INVALID"
    RULE_PARAMS_INVALID = "RULE_PARAMS_INVALID"
    SEED_INVALID = "SEED_INVALID"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class SpecIssue(BaseModel):
    """One finding. `code` is a SpecIssueCode, or a FrontendIssueCode for FrontendSpecs (Story 12.1).
    `backend_path` points into the BackendSpec when the finding is about both specs (Story 12.5)."""

    code: str
    path: str
    message: str
    hint: str | None = None
    severity: Severity = Severity.ERROR
    backend_path: str | None = None


class ValidationReport(BaseModel):
    valid: bool
    spec_version: str | None = None
    errors: list[SpecIssue] = []
    warnings: list[SpecIssue] = []

    @classmethod
    def from_issues(cls, issues: list[SpecIssue], spec_version: str | None) -> "ValidationReport":
        errors = [issue for issue in issues if issue.severity == Severity.ERROR]
        warnings = [issue for issue in issues if issue.severity == Severity.WARNING]
        return cls(valid=not errors, spec_version=spec_version, errors=errors, warnings=warnings)
