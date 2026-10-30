from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends

from src.modules.shared.domain.backend_spec import Severity, SpecIssue, ValidationReport, validate_spec_data
from src.modules.shared.domain.frontend_spec import FrontendIssueCode, validate_frontend_spec_data
from src.orchestrator.checks.consistency import check_spec_pair
from src.orchestrator.contract import build_contract


@dataclass
class SpecPairReport:
    """`checked` is False when the pair could not be compared: one spec is invalid (its own validation says why)
    or the FrontendSpec is static and has no API contract."""

    checked: bool
    report: ValidationReport
    contract: dict[str, Any] | None = None  # the API contract of the BackendSpec (9.7b preview), when checked


class CheckSpecPairUsecase:
    """Frontend ↔ contract consistency (Story 12.5) for two unsaved specs, so the UI can check editor text (9.7a)."""

    async def execute(self, frontend_spec: dict[str, Any], backend_spec: dict[str, Any]) -> SpecPairReport:
        frontend = validate_frontend_spec_data(frontend_spec)
        backend = validate_spec_data(backend_spec)
        if frontend.normalized is None or backend.normalized is None:
            return SpecPairReport(checked=False, report=ValidationReport(valid=False, spec_version=None))
        version = frontend.report.spec_version
        if frontend.normalized["project"]["mode"] == "static":
            issue = SpecIssue(
                code=FrontendIssueCode.FE_UNSUPPORTED_FEATURE,
                path="/project/mode",
                message="Static sites have no API contract; the BackendSpec was not used",
                severity=Severity.WARNING,
            )
            return SpecPairReport(checked=False, report=ValidationReport.from_issues([issue], version))
        issues = check_spec_pair(frontend.normalized, backend.normalized)
        return SpecPairReport(
            checked=True,
            report=ValidationReport.from_issues(issues, version),
            contract=build_contract(backend.normalized),
        )


CheckSpecPairUsecaseDep = Annotated[CheckSpecPairUsecase, Depends(CheckSpecPairUsecase)]
