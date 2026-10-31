import re
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends

from src.configs import config
from src.engines.workspace import WorkspaceViolation, ensure_inside
from src.libs.exceptions import NotFoundException
from src.libs.redaction import default_redactor
from src.modules.generations.ports.output import IArtifactRepoDep, IExecutionRecordRepoDep
from src.modules.generations.usecases.artifact_usecases import artifact_file
from src.modules.generations.usecases.get_generation_usecase import GetGenerationUsecaseDep
from src.modules.shared.domain.entities import GenerationEntity, UserEntity
from src.modules.shared.domain.telemetry import ExecutionRecords, build_spans, rollup

PATCH_NAME = re.compile(r"^repair-(\d+)\.patch$")
MAX_TAIL_BYTES = 2_000_000
MAX_OUTPUT_CHARS = 200_000


class GetTraceUsecase:
    """The local trace (Story 8.3) and usage rollups (8.4) of one generation, built from its execution records."""

    def __init__(self, getter: GetGenerationUsecaseDep, records: IExecutionRecordRepoDep, artifacts: IArtifactRepoDep):
        self.getter = getter
        self.records = records
        self.artifacts = artifacts

    def records_for(self, generation: GenerationEntity) -> ExecutionRecords:
        return ExecutionRecords(
            generation=generation,
            node_runs=self.records.list_node_runs(generation.id),
            invocations=self.records.list_cli_invocations(generation.id),
            model_calls=self.records.list_model_calls(generation.id),
            image_calls=self.records.list_image_calls(generation.id),
            validation_runs=self.records.list_validation_runs(generation.id),
            sandbox_execs=self.records.list_sandbox_execs(generation.id),
        )

    async def trace(self, generation_id: str, user: UserEntity) -> dict[str, Any]:
        generation = self.getter.load(generation_id, user)
        records = self.records_for(generation)
        patches = {
            int(match.group(1)): artifact.id
            for artifact in self.artifacts.list_for_generation(generation_id)
            if (match := PATCH_NAME.match(artifact.name))
        }
        return {
            "generationId": generation.id,
            "status": generation.status,
            "traceId": generation.trace_id,
            "langsmithUrl": generation.langsmith_run_url,
            # Node summaries and file lists come from the engine's work: masked like events (Story 8.1).
            "spans": default_redactor().redact_obj(build_spans(records, patches)),
            "usage": rollup(records),
        }

    async def usage(self, generation_id: str, user: UserEntity) -> dict[str, Any]:
        generation = self.getter.load(generation_id, user)
        return {"generationId": generation.id, **rollup(self.records_for(generation))}

    async def output(
        self, generation_id: str, span_id: str, user: UserEntity, stream: Literal["stdout", "stderr"], tail: int
    ) -> dict[str, Any]:
        """A redacted, size-capped excerpt of what a span produced: CLI output (engine spans), the check's
        output (check spans) or the repair patch (repair spans)."""
        generation = self.getter.load(generation_id, user)
        kind, _, record_id = span_id.partition(":")
        if kind == "engine":
            invocation = next(
                (i for i in self.records.list_cli_invocations(generation.id) if str(i.id) == record_id), None
            )
            ref = (invocation.stdout_ref if stream == "stdout" else invocation.stderr_ref) if invocation else None
            text = _tail_file(_log_path(generation.id, ref), tail) if ref else None
        elif kind == "check":
            run = next((r for r in self.records.list_validation_runs(generation.id) if str(r.id) == record_id), None)
            text = _tail_text(run.details.get("output") or "", tail) if run else None
        elif kind == "node":
            run = next((r for r in self.records.list_node_runs(generation.id) if str(r.id) == record_id), None)
            artifact = (
                self.artifacts.find_by_name(generation.id, f"repair-{run.attempt}.patch")
                if run and run.node == "repair_code"
                else None
            )
            text = _tail_text(artifact_file(artifact).read_text(errors="replace"), tail) if artifact else None
            stream = "patch" if artifact else stream
        else:
            text = None
        if text is None:
            raise NotFoundException("This span has no output")
        redacted = default_redactor().redact(text)
        return {
            "spanId": span_id,
            "stream": stream,
            "text": redacted[-MAX_OUTPUT_CHARS:],
            "truncated": len(redacted) > MAX_OUTPUT_CHARS,
        }


def _log_path(generation_id: str, ref: str) -> Path | None:
    """Engine logs live in the job workspace; the stored ref is only trusted for its file name."""
    logs = Path(config.workspace_root) / generation_id / "state" / "logs"
    try:
        path = ensure_inside(logs / Path(ref).name, logs)
    except WorkspaceViolation:
        return None
    return path if path.is_file() else None


def _tail_file(path: Path | None, lines: int) -> str | None:
    if path is None:
        return None
    with path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - MAX_TAIL_BYTES))
        data = handle.read().decode("utf-8", errors="replace")
    return _tail_text(data, lines)


def _tail_text(text: str, lines: int) -> str:
    return "\n".join(text.splitlines()[-lines:])


GetTraceUsecaseDep = Annotated[GetTraceUsecase, Depends(GetTraceUsecase)]
