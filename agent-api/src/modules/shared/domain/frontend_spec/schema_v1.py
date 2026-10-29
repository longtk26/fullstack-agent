"""FrontendSpec 1.0 (Story 12.1): pages, theme, layout, components, data bindings, forms, content.

Structural contract only; cross-references (pages, forms, components, route parameters, assets) live in
validator.py. `data.operationId` and `forms[].operationId` are the only links to the backend; Story 12.5 checks
them against the API contract.
"""

from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, model_validator

from src.modules.shared.domain.backend_spec.schema_v1 import IDENTIFIER, OPERATION_ID, SpecModel

SLUG = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
COMPONENT_NAME = r"^[A-Z][A-Za-z0-9]*$"
# "/" or segments that are kebab-case words or one `[param]`; no catch-all routes in 1.0
ROUTE = r"^/$|^(/([a-z0-9]+(-[a-z0-9]+)*|\[[a-z][A-Za-z0-9]*\]))+$"
LOCALE = r"^[a-z]{2,3}(-[A-Z]{2})?$"
FONT = r"^[A-Za-z0-9][A-Za-z0-9 ]{0,63}$"

ThemeStyle = Literal["minimal", "editorial", "playful", "corporate", "dashboard"]
FormFieldType = Literal[
    "string", "text", "email", "url", "tel", "password", "integer", "number", "decimal", "boolean", "date",
    "datetime", "enum",
]  # fmt: skip


class Project(SpecModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    mode: Literal["static", "dynamic"]
    locale: str = Field(default="en", pattern=LOCALE)
    locales: list[Annotated[str, Field(pattern=LOCALE)]] = []


class ThemeColors(SpecModel):
    """CSS colours: hex, or rgb()/hsl()/oklch(); checked in the validator (FE_INVALID_COLOR)."""

    primary: str | None = None
    secondary: str | None = None
    accent: str | None = None
    background: str | None = None
    foreground: str | None = None
    muted: str | None = None
    destructive: str | None = None


class Typography(SpecModel):
    heading_font: str | None = Field(default=None, pattern=FONT)
    body_font: str | None = Field(default=None, pattern=FONT)
    scale: Literal["compact", "default", "large"] = "default"


class Theme(SpecModel):
    style: ThemeStyle = "minimal"
    color_scheme: Literal["light", "dark", "light-dark"] = "light"
    colors: ThemeColors = ThemeColors()
    typography: Typography = Typography()
    radius: Literal["none", "sm", "md", "lg", "full"] | None = None
    density: Literal["compact", "comfortable"] | None = None


class NavLink(SpecModel):
    label: str = Field(min_length=1, max_length=60)
    page: str | None = None
    href: str | None = Field(default=None, pattern=r"^(https?://|mailto:|tel:)")

    @model_validator(mode="after")
    def _one_target(self):
        if (self.page is None) == (self.href is None):
            raise ValueError("a link needs exactly one of 'page' or 'href'")
        return self


class Header(SpecModel):
    logo_text: str | None = None
    logo: str | None = None  # "asset:<id>"
    navigation: list[NavLink] = []


class Footer(SpecModel):
    text: str | None = None
    links: list[NavLink] = []


class Layout(SpecModel):
    shell: Literal["header-footer", "sidebar", "blank"] = "header-footer"
    header: Header = Header()
    footer: Footer = Footer()


class Seo(SpecModel):
    title: str | None = None
    description: str | None = None


class DataBinding(SpecModel):
    """Where a section's data comes from: an API operation (dynamic) or a `content` collection (both modes)."""

    operation_id: str | None = Field(default=None, pattern=OPERATION_ID)
    collection: str | None = Field(default=None, pattern=IDENTIFIER)
    params: dict[str, Any] = {}
    fields: list[str] = []  # record fields the section displays; checked against the response (12.5)

    @model_validator(mode="after")
    def _one_source(self):
        if (self.operation_id is None) == (self.collection is None):
            raise ValueError("a data binding needs exactly one of 'operationId' or 'collection'")
        return self


class SectionStates(SpecModel):
    loading: str | None = None
    empty: str | None = None
    error: str | None = None


class Section(SpecModel):
    id: str = Field(pattern=SLUG, max_length=63)
    component: str = Field(pattern=COMPONENT_NAME, max_length=63)
    data: DataBinding | None = None
    form: str | None = None
    content: dict[str, Any] = {}  # typed per built-in component (section_props.py, Story 17.1)
    states: SectionStates | None = None
    children: list["Section"] | None = None  # layout nodes only (Columns, Stack, Grid, Tabs)


class Page(SpecModel):
    id: str | None = Field(default=None, pattern=SLUG, max_length=63)
    route: str = Field(pattern=ROUTE, max_length=255)
    title: str = Field(min_length=1, max_length=120)
    purpose: str | None = None
    seo: Seo | None = None
    sections: list[Section] = Field(min_length=1)


class Component(SpecModel):
    name: str = Field(pattern=COMPONENT_NAME, max_length=63)
    kind: Literal["primitive", "composite", "section", "layout"] = "composite"
    uses: list[str] = []
    description: str | None = None


class FormField(SpecModel):
    name: str = Field(pattern=IDENTIFIER, max_length=63)
    type: FormFieldType = "string"
    label: str | None = None
    required: bool = False
    hidden: bool = False
    value: Any = None  # fixed value or "$route.<param>" (hidden fields)
    values: list[str] | None = None  # enum
    min: float | None = None
    max: float | None = None
    max_length: int | None = Field(default=None, ge=1, le=65535)
    placeholder: str | None = None


class OnSuccess(SpecModel):
    toast: str | None = None
    navigate: str | None = None  # a page id or a route


class Form(SpecModel):
    id: str = Field(pattern=IDENTIFIER, max_length=63)
    operation_id: str | None = Field(default=None, pattern=OPERATION_ID)
    params: dict[str, Any] = {}  # path parameters of the operation, e.g. {"id": "$route.id"}
    fields: list[FormField] = Field(min_length=1)
    submit_label: str | None = None
    on_success: OnSuccess | None = None


class ContentCollection(SpecModel):
    collection: str = Field(pattern=IDENTIFIER, max_length=63)
    records: list[dict[str, Any]] = []


class Asset(SpecModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$", max_length=63)
    kind: Literal["image", "icon", "video", "file"] = "image"
    alt: str | None = None
    source: str = "placeholder"  # "placeholder" or an https:// URL


class FrontendSpecV1(SpecModel):
    model_config = ConfigDict(title="FrontendSpec 1.0")

    spec_version: Literal["1.0"]
    project: Project
    theme: Theme = Theme()
    layout: Layout = Layout()
    pages: list[Page] = Field(min_length=1)
    components: list[Component] = []
    forms: list[Form] = []
    content: list[ContentCollection] = []
    assets: list[Asset] = []
    auth: dict[str, Any] | None = None  # reserved for Epic 10
    backend_spec: str | None = Field(default=None, alias="x-backendSpec")
