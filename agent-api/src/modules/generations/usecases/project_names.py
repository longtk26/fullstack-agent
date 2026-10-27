from src.modules.shared.domain.entities import GenerationEntity
from src.modules.specs.ports.output import IBackendSpecRepository, IFrontendSpecRepository


def project_names(
    generations: list[GenerationEntity],
    backend_specs: IBackendSpecRepository,
    frontend_specs: IFrontendSpecRepository,
) -> dict[str, str | None]:
    """generation id → project name, from the BackendSpec, or the FrontendSpec for static sites."""
    backend = backend_specs.find_by_ids(list({g.spec_id for g in generations if g.spec_id}))
    frontend = frontend_specs.find_by_ids(list({g.frontend_spec_id for g in generations if g.frontend_spec_id}))

    def name(generation: GenerationEntity) -> str | None:
        for spec in (backend.get(generation.spec_id), frontend.get(generation.frontend_spec_id)):
            project = ((spec.normalized_json or {}).get("project") or {}) if spec else {}
            if project.get("name"):
                return project["name"]
        return None

    return {generation.id: name(generation) for generation in generations}
