from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import ProjectEntity


class UpdateProjectRequestDto(BaseModel):
    """PATCH body: only the fields that are sent change."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None

    def to_entity(self, current: ProjectEntity) -> ProjectEntity:
        return current.model_copy(update=self.model_dump(exclude_unset=True))
