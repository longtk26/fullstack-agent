from typing import Annotated, Any

from fastapi import Depends

from src.modules.generations.ports.output import IExecutionRecordRepoDep
from src.modules.generations.usecases.get_generation_usecase import GetGenerationUsecaseDep
from src.modules.shared.domain.entities import UserEntity
from src.orchestrator.validation import CHECKS


class GetValidationUsecase:
    """Every check across every validation attempt (attempt n+1 follows repair n), in pipeline order."""

    def __init__(self, getter: GetGenerationUsecaseDep, records: IExecutionRecordRepoDep):
        self.getter = getter
        self.records = records

    async def execute(self, generation_id: str, user: UserEntity) -> dict[str, Any]:
        self.getter.load(generation_id, user)
        by_check: dict[str, list[dict[str, Any]]] = {}
        attempts: set[int] = set()
        for run in self.records.list_validation_runs(generation_id):
            attempts.add(run.attempt)
            by_check.setdefault(run.check, []).append(
                {
                    "attempt": run.attempt,
                    "status": run.status,
                    "durationMs": run.duration_ms,
                    "summary": run.details.get("summary"),
                    "items": run.details.get("items", []),
                    "output": run.details.get("output") or None,
                }
            )
        order = [check for check in CHECKS if check in by_check] + sorted(set(by_check) - set(CHECKS))
        checks = [{"check": check, "runs": sorted(by_check[check], key=lambda r: r["attempt"])} for check in order]
        return {"attempts": len(attempts), "checks": checks}


GetValidationUsecaseDep = Annotated[GetValidationUsecase, Depends(GetValidationUsecase)]
