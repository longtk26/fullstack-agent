import re
from typing import Any

from .catalogue import BUILTIN_SECTIONS, DEFAULT_STATES, THEME_PRESETS
from .schema_v1 import Component, FrontendSpecV1, SectionStates, Seo

_PARAM = re.compile(r"^\[([A-Za-z][A-Za-z0-9]*)\]$")


def route_params(route: str) -> list[str]:
    return [match.group(1) for part in route.split("/") if (match := _PARAM.match(part))]


def page_id(route: str) -> str:
    """`/` → `home`; `/products/[id]` → `products-id`."""
    parts = [part.strip("[]").lower() for part in route.split("/") if part]
    return "-".join(parts) or "home"


def normalize_frontend_spec(spec: FrontendSpecV1) -> dict[str, Any]:
    """Fills implicit defaults (theme preset values, page ids, the component catalogue, data states), so the
    frontend planner never re-derives them."""
    normalized = spec.model_copy(deep=True)
    project = normalized.project
    project.locales = [project.locale, *[locale for locale in project.locales if locale != project.locale]]

    theme = normalized.theme
    preset = THEME_PRESETS[theme.style]
    for key, value in preset["colors"].items():
        if getattr(theme.colors, key) is None:
            setattr(theme.colors, key, value)
    theme.typography.heading_font = theme.typography.heading_font or preset["typography"]["headingFont"]
    theme.typography.body_font = theme.typography.body_font or preset["typography"]["bodyFont"]
    theme.radius = theme.radius or preset["radius"]
    theme.density = theme.density or preset["density"]
    if normalized.layout.header.logo_text is None and normalized.layout.header.logo is None:
        normalized.layout.header.logo_text = project.name

    declared = {component.name for component in normalized.components}
    for page in normalized.pages:
        page.id = page.id or page_id(page.route)
        page.seo = page.seo or Seo()
        page.seo.title = page.seo.title or page.title
        for section in page.sections:
            if section.component in BUILTIN_SECTIONS and section.component not in declared:
                builtin = BUILTIN_SECTIONS[section.component]
                normalized.components.append(
                    Component(
                        name=section.component,
                        kind="section",
                        uses=list(builtin["uses"]),
                        description=builtin["description"],
                    )
                )
                declared.add(section.component)
            if section.data is not None:
                states = section.states or SectionStates()
                for key, value in DEFAULT_STATES.items():
                    if getattr(states, key) is None:
                        setattr(states, key, value)
                section.states = states
    for form in normalized.forms:
        form.submit_label = form.submit_label or "Submit"
    return normalized.model_dump(by_alias=True, mode="json", exclude_none=True)
