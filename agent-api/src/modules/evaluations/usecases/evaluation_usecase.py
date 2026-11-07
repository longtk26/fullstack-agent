"""Story 26.6: the latest business evaluation of a generation, and "Run again" (Story 26.5)."""

import json
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from src.configs import config
from src.libs.database import SessionDep
from src.libs.exceptions import ErrorCode, NotFoundException, UnprocessableEntityException
from src.libs.redis import get_redis
from src.modules.evaluations.infrastructure.persistence import EvaluationRepository
from src.modules.generations.usecases.get_generation_usecase import GetGenerationUsecaseDep
from src.modules.shared.domain.entities import UserEntity
from src.modules.shared.domain.entities.evaluation_run_entity import EvaluationRunEntity
from src.modules.specs.ports.output import ISpecDraftRepoDep

EVALUATION_QUEUE = "bga:evaluations"


def evaluation_queue(provider: str) -> str:
    """The queue of a provider's evaluations: served by the workers that can call it (Epic 24: agy's account login
    lives on the host worker)."""
    return f"{EVALUATION_QUEUE}:{provider}"


def evaluation_dir(generation_id: str, run_id: str) -> Path:
    return Path(config.artifact_root) / generation_id / "evaluation" / run_id


class EvaluationUsecase:
    def __init__(self, getter: GetGenerationUsecaseDep, session: SessionDep, drafts: ISpecDraftRepoDep):
        self.getter = getter
        self.session = session
        self.drafts = drafts
        self.repo = EvaluationRepository(session)

    def _bound(self, options: dict) -> bool:
        """The generation's draft has bound business workflows (the business layer was on and its binding ran)."""
        try:
            draft = self.drafts.find_by_id(uuid.UUID(str(options.get("draftId"))))
        except (TypeError, ValueError):
            return False
        return bool(draft and (draft.business or {}).get("binding"))

    def latest(self, generation_id: str, user: UserEntity) -> EvaluationRunEntity | None:
        """The latest run; None when nothing ran yet. 404 when the generation has nothing to evaluate: no bound
        workflows and no run against another generation's expectations (the UI shows no Business tab then)."""
        generation = self.getter.load(generation_id, user)
        run = self.repo.latest(generation_id)
        if run is None and not self._bound(generation.options or {}):
            raise NotFoundException("This generation has no bound business workflows")
        return run

    async def run(
        self, generation_id: str, user: UserEntity, expectations_from: str | None = None
    ) -> EvaluationRunEntity:
        """Queues a run. `expectations_from` (Story 26.7): check this app against another generation's frozen
        expectations (e.g. the same requirement generated without the business layer); "Run again" keeps the
        latest run's source."""
        generation = self.getter.load(generation_id, user)
        options = generation.options or {}
        if expectations_from is None and not self._bound(options):
            previous = self.repo.latest(generation_id)
            expectations_from = previous.expectations_from if previous else None
        if expectations_from == generation_id:
            expectations_from = None
        if expectations_from is not None:
            source = self.getter.load(expectations_from, user)
            if not self._bound(source.options or {}):
                raise UnprocessableEntityException(
                    "The generation to take the expectations from has no bound business workflows",
                    code=ErrorCode.VALIDATION_ERROR,
                )
            if generation.mode != "dynamic":
                raise UnprocessableEntityException(
                    "Only a dynamic app can be checked against business workflows", code=ErrorCode.VALIDATION_ERROR
                )
        elif not self._bound(options):
            raise UnprocessableEntityException(
                "Only a generation whose draft has bound business workflows can be evaluated",
                code=ErrorCode.VALIDATION_ERROR,
            )
        provider = options.get("llmProvider") or config.llm_provider_name
        run = self.repo.create(generation_id, "manual", provider, expectations_from)
        self.session.commit()
        message = json.dumps({"evaluationId": str(run.id), "generationId": generation_id})
        await get_redis().rpush(evaluation_queue(provider), message)
        return run

    def screenshot(self, generation_id: str, user: UserEntity, name: str) -> Path:
        run = self.latest(generation_id, user)
        if run is None or "/" in name or "\\" in name or name.startswith("."):
            raise NotFoundException("Screenshot not found")
        path = evaluation_dir(generation_id, str(run.id)) / "shots" / name
        if not path.is_file():
            raise NotFoundException("Screenshot not found")
        return path


EvaluationUsecaseDep = Annotated[EvaluationUsecase, Depends(EvaluationUsecase)]
