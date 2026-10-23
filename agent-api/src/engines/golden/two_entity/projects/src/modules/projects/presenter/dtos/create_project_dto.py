from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import ProjectEntity


class CreateProjectRequestDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str | None = None

    def to_entity(self) -> ProjectEntity:
        return ProjectEntity(name=self.name, description=self.description)
