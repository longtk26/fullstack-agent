"""SVG drawings for site images (Stories 15.2, 15.3): the checks every SVG passes and its React component.

Checks (pure Python on the file, parsed with defusedxml: no DTD, no entities):

    safe        no script, foreignObject, iframe, image, embed, object, style or animation elements; no on* attributes;
                href / xlink:href only to #fragments; url(...) only url(#id); no data: URIs
    valid       root <svg> with a viewBox matching the asset's aspect ratio (±2 %), ≤ 30 KB, ≤ 2 000 elements
    theme       fill / stroke / stop colours only var(--<theme token>), currentColor, none, transparent, url(#id)
    accessible  the component has a <title> or is aria-hidden (decorative)

Uploaded SVGs (15.4) are checked without the theme rule. The converter turns a checked SVG into a component that
takes `className`, with JSX attribute names, the asset's alt text as <title> (or aria-hidden) and ids prefixed with
the asset id so two drawings on one page never share a gradient. It also drops anything the safe rule forbids, so
an unsafe drawing can never reach a page even if it were converted.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from defusedxml import DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden
from defusedxml.ElementTree import ParseError, fromstring

MAX_BYTES = 30 * 1024
MAX_ELEMENTS = 2_000
RATIO_TOLERANCE = 0.02
# The theme's colour variables a drawing may use (named in the prompt, never hex values).
THEME_TOKENS = ("primary", "primary-foreground", "accent", "secondary", "muted", "foreground", "background")
FORBIDDEN = {
    "script", "foreignobject", "iframe", "image", "embed", "object", "style",
    "animate", "animatemotion", "animatetransform", "set", "audio", "video", "canvas",
}  # fmt: skip
COLOUR_PROPERTIES = ("fill", "stroke", "stop-color", "flood-color", "lighting-color", "color")
RATIOS = {"16:9": 16 / 9, "4:3": 4 / 3, "1:1": 1.0, "3:4": 3 / 4, "21:9": 21 / 9}
VIEWBOXES = {"16:9": "0 0 1600 900", "4:3": "0 0 1200 900", "1:1": "0 0 1000 1000", "3:4": "0 0 900 1200",
             "21:9": "0 0 2100 900"}  # fmt: skip
_URL = re.compile(r"url\(\s*([^)]*)\)", re.IGNORECASE)
_VAR = re.compile(r"^var\(--([a-z-]+)\)$")
_DROPPED = {"title", "desc", "metadata"}


@dataclass
class SvgIssue:
    rule: str  # safe | valid | theme | accessible
    message: str

    def as_dict(self, file: str) -> dict[str, str]:
        return {"rule": self.rule, "file": file, "message": self.message}


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _namespace(name: str) -> str:
    return name[1:].split("}", 1)[0] if name.startswith("{") else ""


def parse_svg(text: str):
    """The root element, or an SvgIssue when the document cannot be parsed safely."""
    try:
        return fromstring(text, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden) as exc:
        return SvgIssue("safe", f"DTDs and entities are not allowed ({type(exc).__name__})")
    except ParseError as exc:
        return SvgIssue("valid", f"not well-formed XML: {exc}")


def _style_declarations(style: str) -> list[tuple[str, str]]:
    pairs = []
    for declaration in style.split(";"):
        if ":" in declaration:
            name, value = declaration.split(":", 1)
            pairs.append((name.strip().lower(), value.strip()))
    return pairs


def _colour_ok(value: str) -> bool:
    value = value.strip()
    if value.lower() in ("none", "transparent", "currentcolor", "inherit"):
        return True
    if re.fullmatch(r"url\(\s*#[A-Za-z][\w.-]*\s*\)", value):
        return True
    match = _VAR.match(value)
    return bool(match and match.group(1) in THEME_TOKENS)


def check_svg(text: str, aspect_ratio: str | None, theme: bool = True) -> list[SvgIssue]:
    """Every rule the drawing breaks (empty: it passes)."""
    issues: list[SvgIssue] = []
    size = len(text.encode())
    if size > MAX_BYTES:
        issues.append(SvgIssue("valid", f"{size // 1024} KB, more than {MAX_BYTES // 1024} KB"))
    root = parse_svg(text)
    if isinstance(root, SvgIssue):
        return [*issues, root]
    if _local(root.tag) != "svg":
        issues.append(SvgIssue("valid", f"the root element is <{_local(root.tag)}>, not <svg>"))
    elements = list(root.iter())
    if len(elements) > MAX_ELEMENTS:
        issues.append(SvgIssue("valid", f"{len(elements)} elements, more than {MAX_ELEMENTS}"))
    issues += _check_viewbox(root.get("viewBox"), aspect_ratio)
    seen: set[str] = set()

    def once(issue: SvgIssue) -> None:
        if issue.message not in seen:
            seen.add(issue.message)
            issues.append(issue)

    for element in elements:
        tag = _local(element.tag).lower()
        if tag in FORBIDDEN:
            once(SvgIssue("safe", f"<{_local(element.tag)}> is not allowed"))
        if _namespace(element.tag) not in ("", "http://www.w3.org/2000/svg"):
            once(SvgIssue("safe", f"element from another namespace: {element.tag}"))
        for name, value in element.attrib.items():
            local = _local(name).lower()
            if local.startswith("on"):
                once(SvgIssue("safe", f"event handler attribute '{local}' on <{tag}>"))
            if local == "href" and not value.strip().startswith("#"):
                once(SvgIssue("safe", f"<{tag}> links outside the drawing ({value[:80]})"))
            if "data:" in value.replace(" ", "").lower():
                once(SvgIssue("safe", f"data: URI in '{local}' on <{tag}>"))
            for target in _URL.findall(value):
                if not target.strip().strip("'\"").startswith("#"):
                    once(SvgIssue("safe", f"url({target[:80]}) points outside the drawing"))
            if "@import" in value:
                once(SvgIssue("safe", f"@import in '{local}'"))
            if theme:
                colours = [(local, value)] if local in COLOUR_PROPERTIES else []
                if local == "style":
                    colours += [(k, v) for k, v in _style_declarations(value) if k in COLOUR_PROPERTIES]
                for prop, colour in colours:
                    if not _colour_ok(colour):
                        once(SvgIssue("theme", f'{prop}="{colour[:40]}": use var(--{"|".join(THEME_TOKENS)})'))
        if element.text and "@import" in element.text:
            once(SvgIssue("safe", "@import in text content"))
    return issues


def _check_viewbox(view_box: str | None, aspect_ratio: str | None) -> list[SvgIssue]:
    if not view_box:
        return [SvgIssue("valid", "no viewBox")]
    try:
        _, _, width, height = (float(part) for part in view_box.replace(",", " ").split())
    except ValueError:
        return [SvgIssue("valid", f"viewBox '{view_box}' is not four numbers")]
    if width <= 0 or height <= 0:
        return [SvgIssue("valid", f"viewBox '{view_box}' has no area")]
    wanted = RATIOS.get(aspect_ratio or "")
    if wanted and abs(width / height - wanted) / wanted > RATIO_TOLERANCE:
        return [SvgIssue("valid", f"viewBox {width:g}×{height:g} does not match the aspect ratio {aspect_ratio}")]
    return []


def check_component(text: str) -> list[SvgIssue]:
    """The accessible rule, on the converted component."""
    if "<title>" in text or 'aria-hidden="true"' in text:
        return []
    return [SvgIssue("accessible", "the component has neither a <title> nor aria-hidden")]


# -- SVG → React component ---------------------------------------------------------------------------------------------


def _jsx_name(name: str) -> str:
    namespace, local = _namespace(name), _local(name)
    if namespace == "http://www.w3.org/1999/xlink":
        return "xlink" + local[:1].upper() + local[1:]
    if namespace == "http://www.w3.org/XML/1998/namespace":
        return "xml" + local[:1].upper() + local[1:]
    if local == "class":
        return "className"
    if local.startswith(("aria-", "data-")):
        return local
    head, *rest = local.split("-")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def _jsx_value(value: str) -> str:
    return f'"{value}"' if re.fullmatch(r'[^"\\{}<>\n]*', value) else "{" + json.dumps(value) + "}"


def _style_object(style: str) -> str:
    entries = ", ".join(
        f"{_jsx_name(name)}: {json.dumps(value)}" for name, value in _style_declarations(style) if name and value
    )
    return "{{ " + entries + " }}"


def _prefix_ids(value: str, ids: set[str], prefix: str) -> str:
    def url(match: re.Match) -> str:
        target = match.group(1).strip().strip("'\"")
        return f"url(#{prefix}-{target[1:]})" if target.startswith("#") and target[1:] in ids else match.group(0)

    value = _URL.sub(url, value)
    if value.startswith("#") and value[1:] in ids:
        value = f"#{prefix}-{value[1:]}"
    return value


def svg_to_tsx(text: str, asset: dict[str, Any], component: str) -> str:
    """The React component for a checked SVG (owned file; regenerate rather than edit)."""
    root = parse_svg(text)
    if isinstance(root, SvgIssue):
        raise ValueError(root.message)
    prefix = asset["id"]
    ids = {element.get("id") for element in root.iter() if element.get("id")}
    decorative = bool(asset.get("decorative"))
    alt = asset.get("alt") or asset["id"]

    def unsafe(name: str, value: str) -> bool:
        local = _local(name).lower()
        compact = value.replace(" ", "").lower()
        outside = any(not t.strip().strip("'\"").startswith("#") for t in _URL.findall(value))
        return (
            local.startswith("on")
            or (local == "href" and not value.strip().startswith("#"))
            or ("data:" in compact or "javascript:" in compact or outside)
        )

    def attributes(element, is_root: bool) -> str:
        parts = []
        for name, value in element.attrib.items():
            local = _local(name)
            if unsafe(name, value):
                continue
            if is_root and local in ("width", "height", "class", "style") and not _namespace(name):
                continue
            if local == "xmlns" or name.startswith("{http://www.w3.org/2000/xmlns/}"):
                continue
            value = _prefix_ids(value, ids, prefix)
            if local == "id":
                value = f"{prefix}-{value}"
            jsx = _jsx_name(name)
            parts.append(f"{jsx}={_style_object(value)}" if local == "style" else f"{jsx}={_jsx_value(value)}")
        return (" " + " ".join(parts)) if parts else ""

    def render(element, depth: int) -> list[str]:
        pad = "  " * depth
        tag = _local(element.tag)
        children = [child for child in element if _local(child.tag).lower() not in _DROPPED | FORBIDDEN]
        text_content = (element.text or "").strip()
        if not children and not text_content:
            return [f"{pad}<{tag}{attributes(element, False)} />"]
        lines = [f"{pad}<{tag}{attributes(element, False)}>"]
        if text_content:
            lines.append(f"{pad}  {{{json.dumps(text_content)}}}")
        for child in children:
            lines += render(child, depth + 1)
        lines.append(f"{pad}</{tag}>")
        return lines

    access = 'aria-hidden="true" focusable="false"' if decorative else f'role="img" aria-label={_jsx_value(alt)}'
    body = [f"    <svg{attributes(root, True)} className={{className}} {access}>"]
    if not decorative:
        body.append(f"      <title>{{{json.dumps(alt)}}}</title>")
    for child in root:
        if _local(child.tag).lower() not in _DROPPED | FORBIDDEN:
            body += render(child, 3)
    body.append("    </svg>")
    return (
        f"// Generated from {asset.get('file', 'the asset SVG')} by the Fullstack Generation Agent. Do not edit:\n"
        "// change the SVG (or the FrontendSpec asset) and regenerate.\n"
        f"export default function {component}({{ className }}: {{ className?: string }}) {{\n"
        "  return (\n" + "\n".join(body) + "\n  );\n}\n"
    )
