"""BackendSpec 1.0: the structural contract. Cross-reference rules live in validator.py."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

IDENTIFIER = r"^[A-Za-z][A-Za-z0-9_]*$"
ENTITY_NAME = r"^[A-Z][A-Za-z0-9]*$"
OPERATION_ID = r"^[a-z][a-zA-Z0-9]*(\.[a-zA-Z0-9]+)+$"
API_PATH = r"^/[A-Za-z0-9_\-/{}.]*$"

FieldType = Literal[
    "uuid",
    "string",
    "text",
    "integer",
    "float",
    "decimal",
    "boolean",
    "date",
    "datetime",
    "enum",
    "json",
    "file",
    "image",  # Story 10.5: an uploaded object; the column holds its key
]
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
CrudAction = Literal["create", "get", "list", "update", "delete"]
RuleKind = Literal["transition", "immutableAfter", "ownerOnly", "sumEquals", "custom"]


class SpecModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Project(SpecModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")


class Stack(SpecModel):
    framework: Literal["fastapi"]
    database: Literal["postgresql"]
    orm: Literal["sqlalchemy", "sqlmodel"]
    migration: Literal["alembic"]


class FieldDef(SpecModel):
    name: str = Field(pattern=IDENTIFIER, max_length=63)
    type: FieldType
    primary: bool = False
    required: bool = False
    nullable: bool | None = None
    unique: bool = False
    index: bool = False
    default: Any = None
    values: list[str] | None = None
    max_length: int | None = Field(default=None, ge=1, le=65535)
    min: float | None = None
    max: float | None = None
    description: str | None = None
    # Story 10.5, `file` and `image`: allowed MIME types (`image/*` allowed) and the largest size in bytes
    accept: list[str] | None = None
    max_size: int | None = Field(default=None, ge=1)


class IndexDef(SpecModel):
    fields: list[str] = Field(min_length=1)
    unique: bool = False
    name: str | None = Field(default=None, pattern=IDENTIFIER)


class Entity(SpecModel):
    name: str = Field(pattern=ENTITY_NAME, max_length=63)
    table: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$", max_length=63)
    description: str | None = None
    fields: list[FieldDef] = Field(min_length=1)
    indexes: list[IndexDef] = []
    unique_constraints: list[list[str]] = []
    # Story 10.0b: the field that names a record (a picker's label, a parent's summary); default: the first of
    # `name`, `title`, `label`, `email`, else the first required string field.
    display_field: str | None = Field(default=None, pattern=IDENTIFIER)


class Relationship(SpecModel):
    name: str = Field(pattern=IDENTIFIER)
    type: Literal["one-to-one", "one-to-many", "many-to-many"]
    from_: str = Field(alias="from")
    to: str
    foreign_key: str | None = Field(default=None, pattern=IDENTIFIER)
    on_delete: Literal["CASCADE", "SET NULL", "RESTRICT"] | None = None
    through: str | None = None


class Pagination(SpecModel):
    default_limit: int = Field(default=20, ge=1, le=1000)
    max_limit: int = Field(default=100, ge=1, le=1000)


class PayloadSchema(SpecModel):
    entity: str | None = None
    fields: list[str] | None = None
    properties: list[FieldDef] | None = None
    # A response that is a list of these records (a custom operation's `[{...}, ...]`); omitted: one record.
    type: Literal["object", "array"] | None = None


class Aggregate(SpecModel):
    """Epic 21: a figure computed from an entity's records, written from templates like CRUD (no engine): `fn` of
    `field` (count needs none), optionally grouped by a field, limited to the current period of a date field, and
    filtered by equality. The response is `{"value": n}` or, grouped, `[{"key": "…", "value": n}, …]`."""

    fn: Literal["count", "sum", "avg", "min", "max"]
    field: str | None = None
    group_by: str | None = None
    period: Literal["day", "week", "month", "year"] | None = None
    date_field: str | None = None
    filters: dict[str, Any] = {}


class Operation(SpecModel):
    operation_id: str = Field(pattern=OPERATION_ID, max_length=128)
    type: Literal["crud", "custom", "aggregate"]
    action: CrudAction | None = None
    aggregate: Aggregate | None = None  # Epic 21, with type "aggregate"
    entity: str | None = None
    method: HttpMethod
    path: str = Field(pattern=API_PATH, max_length=255)
    summary: str | None = None
    description: str | None = None
    auth: Literal["none", "jwt"] | None = None
    policy: str | None = None
    request: PayloadSchema | None = None
    response: PayloadSchema | None = None
    pagination: bool | Pagination | None = None
    filters: list[str] = []
    sort: list[str] = []
    search: list[str] = []
    rules: list[str] = []


class Auth(SpecModel):
    type: Literal["jwt"]
    user_entity: str = "User"
    login_field: str = "email"
    roles: list[str] = []


class Policy(SpecModel):
    name: str = Field(pattern=IDENTIFIER)
    type: Literal["role", "ownership"]
    roles: list[str] = []
    owner_field: str | None = None
    # Story 10.3, ownership: roles that reach every record (admins), and what another user's record answers
    bypass_roles: list[str] = []
    deny_status: Literal[403, 404] = 404


class Rule(SpecModel):
    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    kind: RuleKind
    entity: str
    params: dict[str, Any] = {}
    description: str | None = None


class Integration(SpecModel):
    name: str = Field(pattern=IDENTIFIER)
    description: str | None = None
    config: dict[str, Any] = {}


class BackgroundJob(SpecModel):
    name: str = Field(pattern=IDENTIFIER)
    trigger: str | dict[str, Any]
    description: str | None = None


class Seed(SpecModel):
    entity: str
    records: list[dict[str, Any]]


class FrontendBinding(SpecModel):
    page: str
    component_path: str
    component: str
    operation_id: str
    params: dict[str, Any] = {}


class BackendSpecV1(SpecModel):
    model_config = ConfigDict(title="BackendSpec 1.0")

    spec_version: Literal["1.0"]
    project: Project
    stack: Stack
    entities: list[Entity] = []
    relationships: list[Relationship] = []
    operations: list[Operation] = []
    auth: Auth | None = None
    policies: list[Policy] = []
    rules: list[Rule] = []
    integrations: list[Integration] = []
    background_jobs: list[BackgroundJob] = []
    seed: list[Seed] = []
    frontend_bindings: list[FrontendBinding] = Field(default=[], alias="x-frontendBindings")
