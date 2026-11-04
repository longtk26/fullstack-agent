"""TESTING / DEMO ONLY (docs/development/test-doubles.md): the designed pages the fake engine writes (Epic 21).

A real engine designs each page from its content outline; the fake composes a tree from the page's sections with a
few fixed layouts, so drafts with the fake engine render designed pages (and the tree renderer is exercised) without
a model. The composition varies with the draft's seed: the hero's column order and the band treatment.
"""

import json
from pathlib import Path
from typing import Any

from src.modules.shared.domain.frontend_spec.catalogue import BUILTIN_SECTIONS

HEADLINE = "heading font-heading text-4xl font-black leading-[1.05] tracking-tight md:text-6xl"
BODY = "mt-6 max-w-xl text-muted-foreground"
BUTTON = "inline-flex h-10 items-center gap-2 rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground"
OUTLINE = "inline-flex h-10 items-center rounded-md border px-5 text-sm"


def node(kind: str, class_name: str | None = None, children: list[Any] | None = None, **props: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"type": kind, "props": {**({"className": class_name} if class_name else {}), **props}}
    if children is not None:
        out["children"] = children
    return out


def _link(cta: dict[str, Any] | None, class_name: str) -> dict[str, Any] | None:
    if not isinstance(cta, dict) or not cta.get("label"):
        return None
    target = {"to": f"page:{cta['page']}"} if cta.get("page") else {"href": cta.get("href") or "#"}
    return node("Link", class_name, [cta["label"]], **target)


def _hero(content: dict[str, Any], flip: bool) -> dict[str, Any]:
    text = [
        *(
            [
                node(
                    "span",
                    "inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 "
                    "text-xs uppercase tracking-widest text-primary",
                    [node("Sparkles", "size-3.5"), content["eyebrow"]],
                )
            ]
            if content.get("eyebrow")
            else []
        ),
        node("h1", HEADLINE + (" mt-6" if content.get("eyebrow") else ""), [content.get("heading", "")]),
        *([node("p", BODY, [content["body"]])] if content.get("body") else []),
        node(
            "div",
            "mt-8 flex flex-wrap gap-3",
            [link for link in (_link(content.get("cta"), BUTTON), _link(content.get("secondaryCta"), OUTLINE)) if link],
        ),
    ]
    column = node("div", "md:col-span-7", text)
    image = (
        node(
            "figure",
            "md:col-span-5" + (" md:order-first" if flip else ""),
            [
                node(
                    "div",
                    "rounded-3xl border-2 border-primary/20 bg-card p-3 shadow-xl",
                    [node("img", "rounded-2xl", src=content["image"], alt=content.get("heading", ""))],
                )
            ],
            animate={"on": "view", "type": "scale-in", "delay": 0.2},
        )
        if content.get("image")
        else None
    )
    return node(
        "section",
        "mx-auto grid max-w-7xl items-center gap-10 px-6 py-20 md:grid-cols-12",
        [column, *([image] if image else [])],
        animate={"on": "view", "type": "fade-up"},
    )


def _features(content: dict[str, Any]) -> dict[str, Any]:
    cards = [
        node(
            "article",
            "rounded-2xl border bg-card p-6",
            [
                *(
                    [node("Sparkles", "size-5 text-primary")]
                    if not item.get("icon")
                    else [node(_lucide(item["icon"]), "size-5 text-primary")]
                ),
                node("h3", "mt-4 font-heading text-lg", [item.get("title", "")]),
                *([node("p", "mt-2 text-sm text-muted-foreground", [item["body"]])] if item.get("body") else []),
            ],
            animate={"on": "view", "type": "fade-up", "delay": round(0.08 * index, 2)},
        )
        for index, item in enumerate(content.get("items") or [])
    ]
    return node(
        "section",
        "mx-auto max-w-7xl px-6 py-16",
        [
            *([node("h2", "heading font-heading text-3xl", [content["title"]])] if content.get("title") else []),
            node("div", "mt-8 grid gap-6 md:grid-cols-3", cards),
        ],
    )


def _lucide(icon: Any) -> str:
    name = str(icon).split(":", 1)[-1]
    return name if name[:1].isupper() else "Sparkles"


def _stats(content: dict[str, Any], band: bool) -> dict[str, Any]:
    figures = [
        node(
            "div",
            "flex flex-col gap-1",
            [
                node("span", "font-heading text-4xl font-semibold tabular-nums", [str(item.get("value", ""))]),
                node("span", "text-sm text-muted-foreground", [item.get("label", "")]),
            ],
        )
        for item in content.get("items") or []
    ]
    surface = "border-y border-border/60 bg-muted/40 py-12" if band else "py-12"
    return node("section", surface, [node("div", "mx-auto grid max-w-7xl gap-8 px-6 sm:grid-cols-3", figures)])


def _cta(content: dict[str, Any]) -> dict[str, Any]:
    return node(
        "section",
        "mx-auto max-w-7xl px-6 pb-20",
        [
            node(
                "div",
                "rounded-3xl bg-primary px-8 py-12 text-primary-foreground md:flex md:items-center md:justify-between",
                [
                    node(
                        "div",
                        None,
                        [
                            node("h2", "heading font-heading text-3xl", [content.get("heading", "")]),
                            *([node("p", "mt-2 opacity-80", [content["body"]])] if content.get("body") else []),
                        ],
                    ),
                    *(
                        [link]
                        if (
                            link := _link(
                                content.get("cta"),
                                "mt-6 inline-flex h-10 items-center rounded-md bg-background px-5 text-sm font-medium "
                                "text-foreground md:mt-0",
                            )
                        )
                        else []
                    ),
                ],
            ),
        ],
    )


def _bound_section(section: dict[str, Any]) -> dict[str, Any]:
    """A section bound to an API operation stays a library section node (the contract binds it)."""
    data = section.get("data") or {}
    props = {
        "id": section["id"],
        **(section.get("content") or {}),
        "data": {k: v for k, v in data.items() if k != "kind"},
    }
    if section.get("form"):
        props["form"] = section["form"]
    return {"type": section["component"], "props": props}


def _records(section: dict[str, Any], spec: dict[str, Any], detail_pages: dict[str, str]) -> dict[str, Any]:
    data = section.get("data") or {}
    if data.get("operationId"):
        return node("section", "mx-auto max-w-7xl px-6 py-8", [_bound_section(section)])
    collection = data.get("collection") or _collection_for(data.get("operationId"), spec)
    fields = data.get("fields") or _fields_of(collection, spec)[:3]
    title = (section.get("content") or {}).get("title")
    card = node(
        "article",
        "rounded-2xl border bg-card p-4",
        [
            *([node("RecordImage", "rounded-xl", field="image")] if "image" in _fields_of(collection, spec) else []),
            node("h3", "mt-3 font-heading text-lg", [node("RecordField", None, field=fields[0] if fields else "name")]),
            *[
                node("p", "text-sm text-muted-foreground", [node("RecordField", None, field=field)])
                for field in fields[1:3]
            ],
        ],
    )
    if collection in detail_pages:
        card = node("RecordLink", "block", [card], detailSlug=f"page:{detail_pages[collection]}")
    browser = node(
        "CollectionBrowser",
        None,
        [
            node(
                "div",
                "flex flex-wrap items-center gap-3",
                [node("SearchBox", "max-w-xs", placeholder=f"Search {collection}"), node("ResultCount")],
            ),
            node("ItemList", "mt-6 grid gap-6 md:grid-cols-3", [card]),
            node("Empty", "mt-6 text-sm text-muted-foreground", [f"No {collection} yet."]),
            node("Pagination", "mt-6 flex items-center justify-between text-sm"),
        ],
        collection=collection,
        pageSize=9,
        searchFields=[fields[0]] if fields else [],
    )
    return node(
        "section",
        "mx-auto max-w-7xl px-6 py-16",
        [*([node("h2", "heading font-heading text-3xl", [title])] if title else []), browser],
    )


def _detail(section: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    data = section.get("data") or {}
    if data.get("operationId"):
        return node("section", "mx-auto max-w-3xl px-6 py-8", [_bound_section(section)])
    collection = data.get("collection") or _collection_for(data.get("operationId"), spec)
    fields = data.get("fields") or _fields_of(collection, spec)[:6]
    rows = [
        node(
            "div",
            "flex justify-between gap-6 border-b py-3 text-sm",
            [node("dt", "text-muted-foreground", [field]), node("dd", None, [node("RecordField", None, field=field)])],
        )
        for field in fields
    ]
    return node(
        "section",
        "mx-auto max-w-3xl px-6 py-16",
        [
            node(
                "CollectionDetail",
                None,
                [
                    node("h1", HEADLINE, [node("RecordField", None, field=fields[0] if fields else "name")]),
                    node("dl", "mt-8", rows),
                ],
                collection=collection,
            )
        ],
    )


def _collection_for(operation_id: str | None, spec: dict[str, Any]) -> str:
    if operation_id:
        from src.modules.shared.domain.backend_spec.naming import pluralize, to_snake

        return pluralize(to_snake(operation_id.split(".")[0]))
    collections = [c["collection"] for c in spec.get("content") or []]
    return collections[0] if collections else "items"


def _fields_of(collection: str, spec: dict[str, Any]) -> list[str]:
    for item in spec.get("content") or []:
        if item.get("collection") == collection:
            keys: list[str] = []
            for record in item.get("records") or []:
                keys += [k for k in record if k not in keys and k != "id"]
            return keys
    return []


def _section_node(section: dict[str, Any]) -> dict[str, Any]:
    content = dict(section.get("content") or {})
    if section.get("data", {}).get("collection"):
        content["collection"] = section["data"]["collection"]
    return {"type": section["component"], "props": {"id": section["id"], **content}}


def fake_tree(page: dict[str, Any], spec: dict[str, Any], seed: int) -> dict[str, Any]:
    """The page's sections as a designed tree: hero, features, figures, records and the call to action get the
    fake's own layouts; every other section stays a library section node."""
    detail_pages = {}
    for other in spec.get("pages") or []:
        for section in other.get("sections") or []:
            if section.get("component") == "DetailView" and "[" in other.get("route", ""):
                data = section.get("data") or {}
                detail_pages[data.get("collection") or _collection_for(data.get("operationId"), spec)] = other.get(
                    "id"
                ) or other["route"].strip("/").replace("/", "-").replace("[", "").replace("]", "")
    children = []
    for index, section in enumerate(page.get("sections") or []):
        component = section.get("component")
        content = section.get("content") or {}
        if component == "Hero":
            children.append(_hero(content, flip=bool(seed % 2)))
        elif component == "Features" and content.get("items"):
            children.append(_features(content))
        elif component == "Stats" and content.get("items") and not any(i.get("data") for i in content["items"]):
            children.append(_stats(content, band=bool((seed + index) % 2)))
        elif component == "CallToAction":
            children.append(_cta(content))
        elif component in ("CardGrid", "List", "DataTable") and section.get("data"):
            children.append(_records(section, spec, detail_pages))
        elif component == "DetailView" and section.get("data"):
            children.append(_detail(section, spec))
        elif component in BUILTIN_SECTIONS:
            children.append(
                _bound_section(section)
                if (section.get("data") or {}).get("operationId") or section.get("form")
                else _section_node(section)
            )
    return node("main", "relative overflow-x-hidden bg-background text-foreground", children)


def write_tree_fixture(workdir: Path, request_file: Path) -> list[str]:
    """Writes the tree `.bga/tree-<page>.json` asks for (orchestrator/tree_drafting.py) from the current spec."""
    request = json.loads(request_file.read_text())
    spec = json.loads((workdir / "frontend-spec.json").read_text())
    seed = int(json.loads((workdir / ".bga" / "draft.json").read_text()).get("designSeed") or 0)
    output = workdir / request["output_path"]
    output.parent.mkdir(parents=True, exist_ok=True)
    if request["id"] == "chrome":
        return []  # the shell's own header and footer
    page = next((p for p in spec.get("pages") or [] if (p.get("id") or _page_id(p["route"])) == request["id"]), None)
    if page is None:
        return []
    css = (
        ".fake-rug { background-image: radial-gradient(color-mix(in oklch, var(--primary) 6%, transparent) 1.5px, "
        "transparent 1.5px); background-size: 24px 24px; }"
    )
    tree = fake_tree(page, spec, seed)
    tree["props"]["className"] += " fake-rug"
    output.write_text(json.dumps({"tree": tree, "css": css}, indent=2, ensure_ascii=False))
    return [request["output_path"]]


def _page_id(route: str) -> str:
    from src.modules.shared.domain.frontend_spec.normalizer import page_id

    return page_id(route)
