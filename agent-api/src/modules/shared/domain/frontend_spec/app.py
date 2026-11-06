"""The dynamic app flow (Epic 22): the app outline and the app sections, accepted only in dynamic mode.

A FrontendSpec made by the app flow has `project.flow: "app"` and an `app` outline: what the app is (its name,
navigation, home), drafted by the model. Its pages are written by code (the screen planner, Story 22.3) from the
outline and the API contract, as ordinary pages whose sections are the app kit's sections. Static sites and the
legacy dynamic flow never see any of this (decision D1): `site_schema` removes it from the schema their drafts get.
"""

from typing import Annotated, Any, Literal

from pydantic import Field

from src.modules.shared.domain.backend_spec.schema_v1 import ENTITY_NAME, IDENTIFIER, SpecModel

ICON = r"^[A-Z][A-Za-z0-9]*$"  # a Lucide icon name, e.g. "BookOpen"

# The app kit's sections (`templates/nextjs_overlay/files/dynamic/app/`), by FrontendSpec component name.
APP_SECTIONS: dict[str, str] = {
    "AppList": "The records of an entity: a table or cards, with search, filters, sort and pages",
    "AppDetail": "One record: its fields, its actions and a tab per child entity",
    "AppForm": "A create or edit form on the operation's request",
    "AppDashboard": "Figures and charts from aggregates, and recent records",
    "AppActions": "Buttons for operations on a record or a collection",
    # Story 22.7: the plugins' screens (their components live in `templates/plugins/<name>/frontend/files/`)
    "AppAuth": "Sign-in or sign-up on the auth operations (auth-jwt)",
    "AppLinks": "A record's many-to-many links: chips, added with a picker and removed (relations)",
    "AppPayment": "The return from the checkout: the payment's status, polled until it settles (payments)",
}


MAX_LIST_FIELDS = 5  # the fields a list shows
MAX_DASHBOARD = 6  # figures and charts on the dashboard
Aggregate = Literal["count", "sum", "avg", "min", "max"]
Scalar = str | int | float | bool


class AppNavItem(SpecModel):
    entity: str = Field(pattern=ENTITY_NAME, max_length=63)
    label: str | None = Field(default=None, max_length=40)
    icon: str | None = Field(default=None, pattern=ICON, max_length=63)


class AppEntity(SpecModel):
    """How an entity is named and shown; every field is optional (code fills it from the BackendSpec)."""

    label: str | None = Field(default=None, max_length=40)
    plural: str | None = Field(default=None, max_length=40)
    display_field: str | None = Field(default=None, pattern=IDENTIFIER, max_length=63)  # names a record
    list_fields: list[Annotated[str, Field(pattern=IDENTIFIER)]] = Field(default=[], max_length=MAX_LIST_FIELDS)
    list_style: Literal["table", "cards"] | None = None
    detail_fields: list[Annotated[str, Field(pattern=IDENTIFIER)]] = []  # their order on the detail page
    field_labels: dict[str, Annotated[str, Field(max_length=60)]] = {}
    help: dict[str, Annotated[str, Field(max_length=200)]] = {}  # a hint under a form field


class AppDashboardItem(SpecModel):
    """A figure (`kind: figure`) or a chart of an aggregate of an entity's records (Epic 21's aggregates)."""

    label: str = Field(min_length=1, max_length=80)
    kind: Literal["figure", "bar", "line", "area", "pie"] = "figure"
    entity: str = Field(pattern=ENTITY_NAME, max_length=63)
    fn: Aggregate = "count"
    field: str | None = Field(default=None, pattern=IDENTIFIER)  # a number field; none for `count`
    filter: dict[str, Scalar] = {}  # equality on the entity's fields
    period: Literal["day", "week", "month", "year"] | None = None  # records of the current period
    date_field: str | None = Field(default=None, pattern=IDENTIFIER)  # the date `period` reads; default: creation
    group_by: str | None = Field(default=None, pattern=IDENTIFIER)  # a chart's categories


class AppHighlight(SpecModel):
    title: str = Field(min_length=1, max_length=60)
    text: str | None = Field(default=None, max_length=200)
    icon: str | None = Field(default=None, pattern=ICON, max_length=63)


class AppLanding(SpecModel):
    """An optional public first page (off unless the requirement asks for one): a headline, a short text, up to
    three highlights and a button into the app."""

    headline: str = Field(min_length=1, max_length=120)
    text: str | None = Field(default=None, max_length=400)
    highlights: list[AppHighlight] = Field(default=[], max_length=3)
    cta: str | None = Field(default=None, max_length=40)


class AppOutline(SpecModel):
    """What the app is, as the model drafts it: entities, navigation, labels and figures, never layout, routes,
    operations or parameters (code binds every screen, Story 22.3)."""

    name: str | None = Field(default=None, max_length=120)
    tagline: str | None = Field(default=None, max_length=200)
    icon: str | None = Field(default=None, pattern=ICON, max_length=63)
    nav: list[AppNavItem] = []
    home: Literal["dashboard"] | Annotated[str, Field(pattern=ENTITY_NAME)] = "dashboard"
    entities: dict[str, AppEntity] = {}  # by entity name; unknown names are dropped by code
    dashboard: list[AppDashboardItem] = Field(default=[], max_length=MAX_DASHBOARD)
    landing: AppLanding | None = None


def is_app_spec(spec: dict[str, Any]) -> bool:
    """A FrontendSpec made by the app flow (normalized or raw)."""
    return (spec.get("project") or {}).get("flow") == "app"


# Schema parts only the app flow uses: removed from the schema static and legacy dynamic drafts read.
_APP_ONLY_PROPERTIES = {
    "FrontendSpecV1": ("app",),
    "Project": ("flow",),
    "FormField": ("help", "currency", "unit", "reference", "upload", "transition"),
}
_APP_ONLY_DEFS = (
    "AppOutline",
    "AppNavItem",
    "AppEntity",
    "AppDashboardItem",
    "AppLanding",
    "AppHighlight",
    "FormFieldReference",
    "FormFieldUpload",
)


def site_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """The FrontendSpec JSON schema without the app flow's fields (a copy), so the static and legacy drafting prompts
    stay as they were."""
    out = {**schema, "properties": dict(schema.get("properties") or {}), "$defs": dict(schema.get("$defs") or {})}
    for name in _APP_ONLY_PROPERTIES["FrontendSpecV1"]:
        out["properties"].pop(name, None)
    for model, names in _APP_ONLY_PROPERTIES.items():
        if model == "FrontendSpecV1" or model not in out["$defs"]:
            continue
        definition = {**out["$defs"][model], "properties": dict(out["$defs"][model].get("properties") or {})}
        for name in names:
            definition["properties"].pop(name, None)
        out["$defs"][model] = definition
    for name in _APP_ONLY_DEFS:
        out["$defs"].pop(name, None)
    return out
