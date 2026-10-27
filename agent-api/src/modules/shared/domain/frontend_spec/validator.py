import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.modules.shared.domain.backend_spec.issues import Severity, SpecIssue, ValidationReport

from .catalogue import BUILTIN_SECTIONS, SHADCN_PRIMITIVES, THEME_PRESETS
from .issues import FrontendIssueCode
from .normalizer import normalize_frontend_spec, page_id, route_params
from .registry import FRONTEND_SPEC_MODELS
from .schema_v1 import FrontendSpecV1, NavLink

C = FrontendIssueCode
_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_COLOR_FN = re.compile(r"^(rgb|rgba|hsl|hsla|oklch|oklab|lab|lch)\([^()]*\)$")
_ROUTE_REF = re.compile(r"^\$route\.([A-Za-z][A-Za-z0-9]*)$")
MIN_CONTRAST = 4.5  # WCAG AA for body text


@dataclass
class FrontendValidationResult:
    report: ValidationReport
    spec: FrontendSpecV1 | None = None
    normalized: dict[str, Any] | None = None


def validate_frontend_spec_text(raw: str | bytes) -> FrontendValidationResult:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        where = f" (line {exc.lineno}, column {exc.colno})" if isinstance(exc, json.JSONDecodeError) else ""
        issue = SpecIssue(code=C.JSON_MALFORMED, path="", message=f"Body is not valid JSON{where}: {exc}")
        return FrontendValidationResult(ValidationReport.from_issues([issue], None))
    return validate_frontend_spec_data(data)


def validate_frontend_spec_data(data: Any) -> FrontendValidationResult:
    if not isinstance(data, dict):
        issue = SpecIssue(code=C.SCHEMA_VIOLATION, path="", message="FrontendSpec must be a JSON object")
        return FrontendValidationResult(ValidationReport.from_issues([issue], None))

    version = data.get("specVersion")
    model = FRONTEND_SPEC_MODELS.get(version) if isinstance(version, str) else None
    if model is None:
        issue = SpecIssue(
            code=C.SPEC_VERSION_UNSUPPORTED,
            path="/specVersion",
            message=f"Unsupported specVersion {version!r}",
            hint=f"Supported versions: {', '.join(FRONTEND_SPEC_MODELS)}",
        )
        return FrontendValidationResult(ValidationReport.from_issues([issue], None))

    try:
        spec = model.model_validate(data)
    except ValidationError as exc:
        issues = [_schema_issue(error) for error in exc.errors()]
        return FrontendValidationResult(ValidationReport.from_issues(issues, version))

    issues = _SemanticChecker(spec).run()
    report = ValidationReport.from_issues(issues, version)
    return FrontendValidationResult(report, spec, normalize_frontend_spec(spec) if report.valid else None)


def _schema_issue(error: dict[str, Any]) -> SpecIssue:
    path = "".join(f"/{part}" for part in error["loc"])
    message = "Unknown property" if error["type"] == "extra_forbidden" else error["msg"]
    return SpecIssue(code=C.SCHEMA_VIOLATION, path=path, message=message)


def valid_color(value: str) -> bool:
    return bool(_HEX.match(value) or _COLOR_FN.match(value))


def _luminance(hex_color: str) -> float | None:
    digits = hex_color.lstrip("#")
    if len(digits) in (3, 4):
        digits = "".join(ch * 2 for ch in digits[:3])
    elif len(digits) in (6, 8):
        digits = digits[:6]
    else:
        return None
    channels = [int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float | None:
    """WCAG contrast of two hex colours; None when either is not hex."""
    if not (_HEX.match(first) and _HEX.match(second)):
        return None
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def route_key(route: str) -> str:
    return re.sub(r"\[[^\]]+\]", "[]", route)


def route_matches(route: str, target: str) -> bool:
    """`/products/42` matches `/products/[id]`."""
    pattern = "^" + re.sub(r"\\\[[^\]]+\\\]", "[^/]+", re.escape(route)) + "/?$"
    return re.match(pattern, target) is not None


def route_refs(value: Any) -> Iterator[str]:
    """Names used as `$route.<name>` anywhere in a value."""
    if isinstance(value, str):
        match = _ROUTE_REF.match(value)
        if match:
            yield match.group(1)
    elif isinstance(value, dict):
        for item in value.values():
            yield from route_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from route_refs(item)


def _asset_refs(value: Any, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str) and value.startswith("asset:"):
        yield value[len("asset:") :], path
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _asset_refs(item, f"{path}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _asset_refs(item, f"{path}/{index}")


def _page_refs(value: Any, path: str) -> Iterator[tuple[str, str]]:
    """`{"page": "<id>"}` links inside free-form section content (e.g. a hero's call to action)."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "page" and isinstance(item, str):
                yield item, f"{path}/{key}"
            else:
                yield from _page_refs(item, f"{path}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _page_refs(item, f"{path}/{index}")


class _SemanticChecker:
    def __init__(self, spec: FrontendSpecV1):
        self.spec = spec
        self.issues: list[SpecIssue] = []
        self.static = spec.project.mode == "static"
        self.page_ids = [page.id or page_id(page.route) for page in spec.pages]
        self.pages = dict(zip(self.page_ids, spec.pages, strict=True))
        self.components = {component.name for component in spec.components} | set(BUILTIN_SECTIONS)
        self.forms = {form.id: form for form in spec.forms}
        self.assets = {asset.id for asset in spec.assets}
        self.collections = {collection.collection for collection in spec.content}

    def run(self) -> list[SpecIssue]:
        self._check_duplicates()
        self._check_theme()
        self._check_layout()
        self._check_pages()
        self._check_components()
        self._check_forms()
        if self.spec.auth is not None:
            self._add(C.FE_UNSUPPORTED_FEATURE, "/auth", "Auth pages arrive with Epic 10; 'auth' is ignored", True)
        return self.issues

    def _add(self, code: FrontendIssueCode, path: str, message: str, warning: bool = False, hint: str | None = None):
        severity = Severity.WARNING if warning else Severity.ERROR
        self.issues.append(SpecIssue(code=code, path=path, message=message, hint=hint, severity=severity))

    def _unique(self, values: list[str], path: str, what: str, suffix: str = "") -> None:
        seen: dict[str, int] = {}
        for index, value in enumerate(values):
            if value in seen:
                where = f"{path}/{index}{suffix}"
                self._add(C.FE_DUPLICATE_ID, where, f"{what} '{value}' duplicates {path}/{seen[value]}")
            seen.setdefault(value, index)

    def _check_duplicates(self) -> None:
        spec = self.spec
        self._unique(self.page_ids, "/pages", "Page id", "/id")
        routes: dict[str, int] = {}
        for index, page in enumerate(spec.pages):
            key = route_key(page.route)
            if key in routes:
                self._add(
                    C.FE_DUPLICATE_ROUTE,
                    f"/pages/{index}/route",
                    f"Route {page.route} duplicates /pages/{routes[key]}",
                    hint="Routes that differ only in parameter names are the same route",
                )
            routes.setdefault(key, index)
            self._unique([s.id for s in page.sections], f"/pages/{index}/sections", "Section id", "/id")
            params = route_params(page.route)
            if len(params) != len(set(params)):
                self._add(C.SCHEMA_VIOLATION, f"/pages/{index}/route", "Route parameters must be unique")
        if "/" not in routes:
            self._add(C.FE_NO_HOME_PAGE, "/pages", "No page has the route '/'", warning=True)
        self._unique([c.name for c in spec.components], "/components", "Component", "/name")
        self._unique([f.id for f in spec.forms], "/forms", "Form id", "/id")
        self._unique([a.id for a in spec.assets], "/assets", "Asset id", "/id")
        self._unique([c.collection for c in spec.content], "/content", "Content collection", "/collection")
        for f_index, form in enumerate(spec.forms):
            self._unique([field.name for field in form.fields], f"/forms/{f_index}/fields", "Form field", "/name")

    def _check_theme(self) -> None:
        theme = self.spec.theme
        preset = THEME_PRESETS[theme.style]["colors"]
        for key, value in theme.colors.model_dump().items():
            if value is not None and not valid_color(value):
                self._add(
                    C.FE_INVALID_COLOR,
                    f"/theme/colors/{key}",
                    f"'{value}' is not a CSS colour",
                    hint="Use #rgb, #rrggbb or rgb()/hsl()/oklch()",
                )
        foreground = theme.colors.foreground or preset["foreground"]
        background = theme.colors.background or preset["background"]
        ratio = contrast_ratio(foreground, background) if valid_color(foreground) and valid_color(background) else None
        if ratio is not None and ratio < MIN_CONTRAST:
            self._add(
                C.FE_LOW_CONTRAST,
                "/theme/colors/foreground",
                f"Foreground on background has contrast {ratio:.2f}:1, below {MIN_CONTRAST}:1 (WCAG AA)",
                warning=True,
            )

    def _check_link(self, link: NavLink, path: str) -> None:
        if link.page is None:
            return
        page = self.pages.get(link.page)
        if page is None:
            self._add(C.FE_UNKNOWN_PAGE, f"{path}/page", f"Unknown page '{link.page}'", hint=self._known_pages())
        elif route_params(page.route):
            self._add(
                C.FE_ROUTE_PARAM_UNBOUND,
                f"{path}/page",
                f"Page '{link.page}' ({page.route}) needs route parameters a navigation link cannot fill",
            )

    def _known_pages(self) -> str:
        return f"Known pages: {', '.join(self.page_ids)}"

    def _check_layout(self) -> None:
        layout = self.spec.layout
        for index, link in enumerate(layout.header.navigation):
            self._check_link(link, f"/layout/header/navigation/{index}")
        for index, link in enumerate(layout.footer.links):
            self._check_link(link, f"/layout/footer/links/{index}")
        if layout.header.logo:
            for asset, path in _asset_refs(layout.header.logo, "/layout/header/logo"):
                if asset not in self.assets:
                    self._add(C.FE_UNKNOWN_ASSET, path, f"Unknown asset '{asset}'")

    def _check_route_refs(self, value: Any, params: list[str], path: str, where: str) -> None:
        for name in route_refs(value):
            if name not in params:
                self._add(
                    C.FE_ROUTE_PARAM_UNBOUND,
                    path,
                    f"'$route.{name}' is not a parameter of {where}",
                    hint=f"Route parameters: {', '.join(params) or '(none)'}",
                )

    def _check_pages(self) -> None:
        for p_index, page in enumerate(self.spec.pages):
            params = route_params(page.route)
            for s_index, section in enumerate(page.sections):
                path = f"/pages/{p_index}/sections/{s_index}"
                if section.component not in self.components:
                    self._add(
                        C.FE_UNKNOWN_COMPONENT,
                        f"{path}/component",
                        f"Component '{section.component}' is neither built in nor declared in 'components'",
                        hint=f"Built in: {', '.join(BUILTIN_SECTIONS)}",
                    )
                data = section.data
                if data is not None:
                    if data.operation_id is not None and self.static:
                        self._add(
                            C.FE_STATIC_HAS_BINDING,
                            f"{path}/data/operationId",
                            "Static sites have no backend; show data from 'content' instead",
                        )
                    if data.collection is not None and data.collection not in self.collections:
                        self._add(C.FE_UNKNOWN_CONTENT, f"{path}/data/collection", f"No content '{data.collection}'")
                    self._check_route_refs(data.params, params, f"{path}/data/params", page.route)
                if section.form is not None:
                    form = self.forms.get(section.form)
                    if form is None:
                        self._add(C.FE_UNKNOWN_FORM, f"{path}/form", f"Unknown form '{section.form}'")
                    else:
                        form_params = {**form.params, **{f.name: f.value for f in form.fields}}
                        self._check_route_refs(form_params, params, f"{path}/form", f"{page.route} (form '{form.id}')")
                for asset, asset_path in _asset_refs(section.content, f"{path}/content"):
                    if asset not in self.assets:
                        self._add(C.FE_UNKNOWN_ASSET, asset_path, f"Unknown asset '{asset}'")
                for target, link_path in _page_refs(section.content, f"{path}/content"):
                    self._check_link(NavLink(label="link", page=target), link_path.removesuffix("/page"))

    def _check_components(self) -> None:
        known = SHADCN_PRIMITIVES | self.components
        for c_index, component in enumerate(self.spec.components):
            for u_index, name in enumerate(component.uses):
                if name not in known:
                    self._add(
                        C.FE_UNKNOWN_COMPONENT,
                        f"/components/{c_index}/uses/{u_index}",
                        f"'{name}' is not a shadcn primitive or a known component",
                    )

    def _check_forms(self) -> None:
        for f_index, form in enumerate(self.spec.forms):
            path = f"/forms/{f_index}"
            if form.operation_id is not None and self.static:
                self._add(
                    C.FE_STATIC_HAS_BINDING,
                    f"{path}/operationId",
                    "Static sites have no backend; a static form cannot call an operation",
                )
            for i, field in enumerate(form.fields):
                if field.type == "enum" and not field.values:
                    self._add(C.SCHEMA_VIOLATION, f"{path}/fields/{i}/values", "Enum fields need 'values'")
            navigate = form.on_success.navigate if form.on_success else None
            if navigate is None:
                continue
            if navigate.startswith("/"):
                if not any(route_matches(page.route, navigate) for page in self.spec.pages):
                    self._add(C.FE_UNKNOWN_PAGE, f"{path}/onSuccess/navigate", f"No page has the route {navigate}")
            elif navigate not in self.pages:
                self._add(
                    C.FE_UNKNOWN_PAGE,
                    f"{path}/onSuccess/navigate",
                    f"Unknown page '{navigate}'",
                    hint=self._known_pages(),
                )
