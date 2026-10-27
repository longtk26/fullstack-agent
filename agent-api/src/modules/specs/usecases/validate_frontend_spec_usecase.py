import uuid
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import ErrorCode, NotFoundException, UnprocessableEntityException
from src.libs.security import ensure_owner
from src.modules.shared.domain.backend_spec import Severity, SpecIssue, ValidationReport
from src.modules.shared.domain.entities import UserEntity
from src.modules.shared.domain.frontend_spec import FrontendIssueCode, validate_frontend_spec_text
from src.modules.specs.ports.output import IBackendSpecRepoDep
from src.orchestrator.checks.consistency import check_spec_pair


class ValidateFrontendSpecUsecase:
    """Story 12.1 validation, plus the frontend ↔ contract consistency check (12.5) against a stored BackendSpec."""

    def __init__(self, spec_repo: IBackendSpecRepoDep):
        self.spec_repo = spec_repo

    async def execute(self, raw: bytes, user: UserEntity, backend_spec_id: uuid.UUID | None = None) -> ValidationReport:
        backend = None
        if backend_spec_id is not None:
            stored = self.spec_repo.find_by_id(backend_spec_id)
            if stored is None:
                raise NotFoundException("BackendSpec not found")
            ensure_owner(stored.owner_id, user.id, user.is_admin, resource="BackendSpec")
            if stored.normalized_json is None:
                raise UnprocessableEntityException(
                    "The BackendSpec is invalid; fix it before checking the FrontendSpec against it",
                    code=ErrorCode.SPEC_INVALID,
                )
            backend = stored.normalized_json

        result = validate_frontend_spec_text(raw)
        report = result.report
        if backend is None or result.normalized is None:
            return report
        issues = [*report.errors, *report.warnings]
        if result.normalized["project"]["mode"] == "static":
            issues.append(
                SpecIssue(
                    code=FrontendIssueCode.FE_UNSUPPORTED_FEATURE,
                    path="/project/mode",
                    message="Static sites have no API contract; the BackendSpec was not used",
                    severity=Severity.WARNING,
                )
            )
        else:
            issues += check_spec_pair(result.normalized, backend)
        return ValidationReport.from_issues(issues, report.spec_version)


ValidateFrontendSpecUsecaseDep = Annotated[ValidateFrontendSpecUsecase, Depends(ValidateFrontendSpecUsecase)]
