"""Summaries of referenced records (Story 10.0b): `{id, label}`, so a client shows a name, never an id."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# Labels of referenced records by reference name and id, as a repository's `references()` returns them
References = dict[str, dict[Any, str | None]]


class ProjectSummaryDto(BaseModel):
    """A Project as the records that refer to it show it."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    label: str | None
