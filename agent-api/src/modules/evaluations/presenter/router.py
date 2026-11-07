from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import FileResponse
from pydantic import Field

from src.libs.dtos import CamelModel
from src.modules.auth.presenter import CurrentUserDep
from src.modules.evaluations.usecases import EvaluationUsecaseDep
from src.modules.shared.domain.entities.evaluation_run_entity import EvaluationRunEntity

evaluation_router = APIRouter(prefix="/api/v1/generations/{generation_id}/evaluation", tags=["evaluations"])


def _dto(run: EvaluationRunEntity) -> dict[str, Any]:
    """Story 26.6: what the Business tab reads (camelCase, the report as stored)."""
    return {
        "evaluationId": str(run.id),
        "generationId": run.generation_id,
        "status": run.status,
        "trigger": run.trigger,
        "provider": run.provider,
        "expectationsFrom": run.expectations_from,
        "progress": run.progress,
        "score": run.score,
        "report": run.report,
        "usage": run.usage,
        "error": run.error,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
        "startedAt": run.started_at.isoformat() if run.started_at else None,
        "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
        "informationOnly": True,
    }


@evaluation_router.get("")
async def get_evaluation(generation_id: str, user: CurrentUserDep, usecase: EvaluationUsecaseDep) -> dict[str, Any]:
    """404: nothing to evaluate (no Business tab); `status: "NONE"`: workflows bound, no run yet."""
    run = usecase.latest(generation_id, user)
    if run is None:
        return {"generationId": generation_id, "status": "NONE", "informationOnly": True}
    return _dto(run)


class RunEvaluationDto(CamelModel):
    # Story 26.7: the generation whose frozen expectations to check this app against (empty: its own)
    expectations_from: str | None = Field(default=None, max_length=32)


@evaluation_router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run_evaluation(
    generation_id: str, user: CurrentUserDep, usecase: EvaluationUsecaseDep, body: RunEvaluationDto | None = None
) -> dict[str, Any]:
    return _dto(await usecase.run(generation_id, user, body.expectations_from if body else None))


@evaluation_router.get("/shots/{name}")
async def get_screenshot(
    generation_id: str, name: str, user: CurrentUserDep, usecase: EvaluationUsecaseDep
) -> FileResponse:
    return FileResponse(usecase.screenshot(generation_id, user, name), media_type="image/png")
