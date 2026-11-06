"""Story 23.0 prototype harness: requirement → spec with a design brief → UI, to look at before Epic 23 is built.
Dev tool only; nothing here is product code (the product flow is `drafting/app.py` and the app kit).

    make app-design-proto ARGS="draft"                     # paid: one Gemini API call per requirement (+ repairs)
    make app-design-proto ARGS="draft --app news-feed"
    make app-design-proto ARGS="build"                     # no model call: builds the stored drafts, screenshots
    make app-design-proto ARGS="page"                      # only rewrites index.html from the last build

`draft` runs the real app flow (`drafting.app.draft_app`) on the Gemini API engine with a prototype prompt
(`prompts/draft_app/v3proto.md`: v2 plus the design brief) and the answer schema with `design` in the outline. The
brief is taken out of the outline before code completes it (its list styles and home applied first, Epic 23 D6);
the draft is stored under `.data/prototypes/app-design/drafts/<app>/`.

`build` checks each brief against its BackendSpec (prototype `apply_design`), scaffolds the app like
`make design-check-app`, adds the prototype overlay (`overlay/`: top bar shell, media grid / feed / role cards,
twelve style recipes; `?proto=off` is today's kit, `?look=<recipe>` a look), builds it in the Node sandbox and takes
first-screen screenshots, then writes `.data/prototypes/app-design/<date>/index.html`.
"""

import argparse
import asyncio
import json
import shutil
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / ".data" / "prototypes" / "app-design"
DRAFTS = OUT / "drafts"
REQUIREMENTS = HERE / "requirements"

ARCHETYPES = ["back-office", "catalogue", "feed", "workspace", "booking", "learning", "storefront"]
SHELLS = ["sidebar", "topbar", "topbar-tabs", "rail"]
HOMES = ["dashboard", "feed", "catalogue", "agenda", "bento"]
VIEWS = ["table", "cards", "media-grid", "feed", "board", "calendar"]
RECIPES = [
    "minimal",
    "swiss",
    "material",
    "enterprise",
    "soft",
    "clay",
    "glass",
    "aurora",
    "brutalist",
    "neon",
    "playful",
    "editorial",
]
FRAMES = {"catalogue": "wide", "storefront": "wide", "learning": "wide", "feed": "narrow"}

STR = {"type": "string"}
DESIGN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "How the app is presented (Story 23.0 design brief); every value from its list",
    "properties": {
        "archetype": {"type": "string", "enum": ARCHETYPES},
        "shell": {"type": "string", "enum": SHELLS},
        "mobileNav": {"type": "string", "enum": ["drawer", "bottom-tabs"]},
        "homeView": {"type": "string", "enum": HOMES},
        "mainEntity": STR,
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entity": STR,
                    "view": {"type": "string", "enum": VIEWS},
                    "roles": {
                        "type": "object",
                        "properties": {
                            "media": STR,
                            "title": STR,
                            "subtitle": STR,
                            "meta": {"type": "array", "items": STR, "maxItems": 3},
                            "badge": STR,
                            "stat": STR,
                            "price": STR,
                            "avatar": STR,
                        },
                    },
                },
                "required": ["entity", "view", "roles"],
            },
        },
        "looks": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {"recipe": {"type": "string", "enum": RECIPES}, "reason": STR},
                "required": ["recipe", "reason"],
            },
        },
        "reason": STR,
    },
    "required": ["archetype", "shell", "mobileNav", "homeView", "mainEntity", "entities", "looks", "reason"],
}
LAYOUT_KEYS = ["archetype", "shell", "mobileNav", "homeView", "mainEntity", "entities"]
DESIGN_SCHEMA["properties"]["areas"] = {
    "type": "array",
    "description": "Only when groups of roles use the app in clearly different ways: one layout per group",
    "items": {
        "type": "object",
        "properties": {
            "id": STR,
            "label": STR,
            "roles": {"type": "array", "items": STR},
            **{key: DESIGN_SCHEMA["properties"][key] for key in LAYOUT_KEYS},
        },
        "required": ["id", "label", "roles", *LAYOUT_KEYS],
    },
}

# The product types of UI UX Pro Max's data (ranked by code) → archetype candidates for the prompt.
ARCHETYPE_WORDS = {
    "feed": ("news", "blog", "social", "community", "magazine", "content", "media"),
    "catalogue": ("video", "streaming", "music", "podcast", "gallery", "photo", "library", "portfolio"),
    "learning": ("education", "course", "learning", "lms", "e-learning", "school", "training"),
    "storefront": ("e-commerce", "ecommerce", "shop", "store", "marketplace", "retail"),
    "booking": ("booking", "reservation", "hotel", "travel", "restaurant", "appointment", "event"),
    "workspace": ("project", "task", "productivity", "collaboration", "kanban"),
    "back-office": ("dashboard", "admin", "crm", "erp", "analytics", "saas", "b2b", "finance", "inventory"),
}


def archetype_candidates(requirement: str) -> tuple[list[str], list[str]]:
    from src.orchestrator.drafting.design_direction import design_data, rank_products

    data = design_data()
    names = [data.products[index].get("Product Type", "") for index, _ in rank_products(requirement, data)[:3]]
    found: list[str] = []
    for name in names:
        lower = name.lower()
        for archetype, words in ARCHETYPE_WORDS.items():
            if any(word in lower for word in words) and archetype not in found:
                found.append(archetype)
    return found or ["back-office"], names


# ---- draft ------------------------------------------------------------------------------------------------------


def with_design(schema: dict[str, Any]) -> dict[str, Any]:
    outline = schema["$defs"]["AppOutline"]
    outline["properties"]["design"] = DESIGN_SCHEMA
    outline["required"] = sorted({*outline.get("required", []), "design"})
    return schema


def take_design(work: Path, outline_file: str) -> dict[str, Any] | None:
    """The brief out of the drafted outline (which code completes without it); its list styles and home go into the
    outline first, before the contract is built (Epic 23 D6)."""
    path = work / outline_file
    if not path.is_file():
        return None
    outline = json.loads(path.read_text())
    if not isinstance(outline, dict) or not isinstance(outline.get("design"), dict):
        return None
    design = outline.pop("design")
    areas = [a for a in design.get("areas") or [] if isinstance(a, dict)]
    if areas and any(a.get("homeView") == "dashboard" for a in areas):
        outline["home"] = "dashboard"  # one home page per app until areas have their own routes (Story 23.10)
    elif design.get("homeView") in ("feed", "catalogue", "agenda") and design.get("mainEntity"):
        outline["home"] = design["mainEntity"]
    entities = outline.setdefault("entities", {})
    items = design.get("entities") or []
    if isinstance(items, dict):  # keyed by entity (seen live), not the schema's list
        items = [{"entity": key, **(value if isinstance(value, dict) else {})} for key, value in items.items()]
    for item in items:
        if isinstance(item, dict) and item.get("entity"):
            style = "table" if item.get("view") in ("table", "calendar") else "cards"
            entities.setdefault(item["entity"], {})["listStyle"] = style
    path.write_text(json.dumps(outline, indent=2, ensure_ascii=False) + "\n")
    return design


async def draft_one(name: str) -> None:
    from src.configs import config
    from src.engines.port import EngineContext, EngineRequest, EngineResult
    from src.engines.prompts import PromptLibrary, RenderedPrompt
    from src.engines.registry import build_engine_registry
    from src.modules.shared.domain.entities import SpecDraftEntity
    from src.modules.shared.domain.enums import GenerationMode, SpecSource
    from src.orchestrator.drafting import app as app_flow
    from src.orchestrator.drafting.drafts import (
        BACKEND_FILE,
        FRONTEND_FILE,
        check_draft,
        draft_directions,
        inline_inputs,
        usage_record,
        write_inputs,
    )

    requirement = (REQUIREMENTS / f"{name}.md").read_text()
    engine = build_engine_registry(config).get("gemini_api")
    draft = SpecDraftEntity(
        owner_id=uuid.uuid4(),
        source=SpecSource.REQUIREMENT,
        mode=GenerationMode.DYNAMIC,
        requirement_text=requirement,
        requirement_format="markdown",
        requirement_file_name=f"{name}.md",
        engine=engine.name,
    )
    root = Path(config.workspace_root) / "proto-drafts" / f"{name}-{uuid.uuid4().hex[:6]}"
    work, state = root / "work", root / "state"
    work.mkdir(parents=True)
    state.mkdir(parents=True)
    found = draft_directions(draft)
    context = write_inputs(work, draft, REPO / "examples", None, None, app=True)
    context["inline"] = True
    context |= inline_inputs(work, context)
    candidates, products = archetype_candidates(requirement)
    context["archetype_candidates"] = ", ".join(candidates)

    base = PromptLibrary()
    proto = PromptLibrary(HERE / "prompts")

    class Prompts(PromptLibrary):
        def render(self, purpose: str, version: str = "v1", **ctx: Any) -> RenderedPrompt:
            if purpose == "draft_app":
                return proto.render("draft_app", "v3proto", **ctx)
            return base.render(purpose, version, **ctx)

    original = app_flow.app_answer_schema
    app_flow.app_answer_schema = lambda *names: with_design(original(*names))
    calls: list[dict[str, Any]] = []
    brief: dict[str, Any] | None = None
    prompts_used: list[str] = []

    async def call(step: str, prompt: RenderedPrompt, response_schema: dict[str, Any] | None = None) -> EngineResult:
        nonlocal brief
        await engine.prepare_workspace(work, EngineContext(conventions=base.draft_conventions()))
        result = await engine.run(
            EngineRequest(
                purpose=prompt.ref.id,
                workdir=work,
                state_dir=state,
                prompt=prompt.text,
                prompt_ref=prompt.ref,
                response_schema=response_schema,
            )
        )
        calls.append({"step": step, **usage_record(result, prompt)})
        prompts_used.append(f"<!-- {step}: {prompt.ref.id}@{prompt.ref.version} -->\n{prompt.text}")
        if step == "draft":
            brief = take_design(work, app_flow.OUTLINE_FILE)
        print(f"  {name}: {step} {result.status} in {result.duration_ms / 1000:.1f}s")
        return result

    async def progress(message: str, **_: Any) -> None:
        print(f"  {name}: {message}")

    started = time.monotonic()
    try:
        outcome = await app_flow.draft_app(
            work,
            context,
            Prompts(),
            call,
            progress,
            check_draft,
            found[0] if found else None,
            BACKEND_FILE,
            FRONTEND_FILE,
        )
    finally:
        app_flow.app_answer_schema = original
    out = DRAFTS / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for file in (BACKEND_FILE, FRONTEND_FILE, app_flow.OUTLINE_FILE, "notes.json"):
        if (work / file).is_file():
            shutil.copy(work / file, out / file)
    (out / "design-brief.json").write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n")
    (out / "prompts.md").write_text("\n\n".join(prompts_used))
    summary = {
        "requirement": f"{name}.md",
        "ok": bool(outcome.check.ok),
        "error": outcome.error,
        "repairs": outcome.attempts,
        "seconds": round(time.monotonic() - started, 1),
        "archetypeCandidates": candidates,
        "productTypes": products,
        "direction": (found[0] or {}).get("name") if found else None,
        "notes": outcome.notes,
        "unresolved": outcome.unresolved,
        "calls": calls,
        "costUsd": round(sum(c["costUsd"] or 0 for c in calls), 4),
    }
    (out / "draft.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n")
    shutil.rmtree(root, ignore_errors=True)
    print(f"{name}: {'ok' if summary['ok'] else 'INVALID'}, {len(calls)} call(s), ${summary['costUsd']} → {out}")


# ---- apply_design (prototype) -----------------------------------------------------------------------------------

IMAGE_WORDS = ("image", "thumbnail", "cover", "logo", "banner", "avatar", "photo", "picture")
DATES = ("date", "datetime")
ROLE_ORDER = ["title", "media", "avatar", "price", "stat", "badge", "subtitle", "meta"]  # who keeps a shared field


def _is_image(field: dict[str, Any]) -> bool:
    return field.get("type") in ("image", "file") or (
        field.get("type") == "string" and any(word in field["name"].lower() for word in IMAGE_WORDS)
    )


def _fits(role: str, field: dict[str, Any]) -> bool:
    if role in ("media", "avatar"):
        return _is_image(field)
    if role in ("stat", "price"):
        return field.get("type") in ("integer", "number", "decimal", "float")
    return True


def _shared(roles: dict[str, Any], value: str) -> str:
    return next(r for r, x in roles.items() if value in (x if isinstance(x, list) else [x]))


def _entity(name: str, item: dict[str, Any], fields: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    roles: dict[str, Any] = {}
    used: set[str] = set()
    order = sorted(
        (item.get("roles") or {}).items(), key=lambda kv: ROLE_ORDER.index(kv[0]) if kv[0] in ROLE_ORDER else 99
    )
    for role, value in order:
        values = value if isinstance(value, list) else [value]
        for v in [v for v in values if v in used]:
            notes.append(f"{name}: {role} '{v}' dropped (already the {_shared(roles, v)})")
        values = [v for v in values if v not in used]
        kept = [v for v in values if v in fields and _fits(role, fields[v])]
        used.update(kept)
        for v in values:
            if v not in kept:
                why = "no such field" if v not in fields else f"a {fields[v].get('type')} field can't be the {role}"
                notes.append(f"{name}: {role} '{v}' dropped ({why})")
        if kept:
            roles[role] = kept if role == "meta" else kept[0]
    if "media" not in roles:
        image = next((f for f, spec in fields.items() if _is_image(spec) and "avatar" not in f.lower()), None)
        if image and image not in used:
            roles["media"] = image
    view = item.get("view") or "table"
    if view == "media-grid" and "media" not in roles:
        notes.append(f"{name}: media-grid needs an image field; shown as cards")
        view = "cards"
    extra: dict[str, Any] = {}
    if view == "board":
        status = next(
            (f for f in [roles.get("badge"), "status", *fields] if f in fields and fields[f].get("type") == "enum"),
            None,
        )
        if status:
            extra["groupBy"] = status
            notes.append(f"{name}: board by '{status}' (prototype: the loaded page only; drag needs Story 23.4)")
        else:
            notes.append(f"{name}: board needs a status field; shown as cards")
            view = "cards"
    if view == "calendar":
        dates = [f for f in [*(roles.get("meta") or []), *fields] if fields.get(f, {}).get("type") in DATES]
        date_field = next((f for f in dates if f not in ("createdAt", "updatedAt")), dates[0] if dates else None)
        if date_field:
            extra["dateField"] = date_field
            notes.append(f"{name}: calendar by '{date_field}' (prototype: the loaded page; ranges need Story 23.4)")
        else:
            notes.append(f"{name}: calendar needs a date field; shown as a table")
            view = "table"
    return {"view": view, "roles": roles, **extra}


def _layout(src: dict[str, Any], entities: dict[str, Any], notes: list[str], where: str) -> dict[str, Any]:
    """One layout (the app's, or an area's) checked against the BackendSpec."""
    main = src.get("mainEntity")
    if main not in entities:
        notes.append(f"{where}mainEntity '{main}' is not an entity; the first entity is used")
        main = next(iter(entities), "")
    out: dict[str, Any] = {
        "archetype": src.get("archetype") if src.get("archetype") in ARCHETYPES else "back-office",
        "shell": src.get("shell") if src.get("shell") in SHELLS else "sidebar",
        "mobileNav": src.get("mobileNav") or "drawer",
        "homeView": src.get("homeView") or "dashboard",
        "mainEntity": main,
        "entities": {},
    }
    if out["shell"] == "rail":
        notes.append(f"{where}shell 'rail' is shown as the kit's sidebar in the prototype")
    if out["homeView"] == "bento":
        notes.append(f"{where}home 'bento' is not prototyped; the dashboard is the home page")
        out["homeView"] = "dashboard"
    out["frame"] = FRAMES.get(out["archetype"], "standard")
    items = src.get("entities") or []
    if isinstance(items, dict):  # seen live (2026-11-06): keyed by entity instead of the schema's list
        notes.append(f"{where}entities came as an object (the answer schema asks for a list); read as is")
        items = [{"entity": name, **(value if isinstance(value, dict) else {})} for name, value in items.items()]
    for item in items:
        name = item.get("entity")
        if name not in entities:
            notes.append(f"{where}entity '{name}' is not in the BackendSpec; left out")
            continue
        out["entities"][name] = _entity(f"{where}{name}", item, entities[name], notes)
    if out["homeView"] == "agenda" and out["entities"].get(main, {}).get("view") != "calendar":
        notes.append(f"{where}home 'agenda' needs the main entity on a calendar; the dashboard is the home page")
        out["homeView"] = "dashboard"
    return out


def apply_design(brief: dict[str, Any], backend: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The brief checked against the BackendSpec: what fits is kept, the rest replaced with a note (Epic 23 D1)."""
    notes: list[str] = []
    entities = {e["name"]: {f["name"]: f for f in e.get("fields") or []} for e in backend.get("entities") or []}
    out = {**_layout(brief, entities, notes, ""), "looks": [], "reason": brief.get("reason") or "", "areas": []}
    roles = list(((backend.get("auth") or {}).get("roles")) or [])
    seen: set[str] = set()
    for area in brief.get("areas") or []:
        if not isinstance(area, dict):
            continue
        where = f"area '{area.get('id')}': "
        own = [r for r in area.get("roles") or [] if r in roles and r not in seen]
        for role in area.get("roles") or []:
            if role not in own:
                notes.append(
                    f"{where}role '{role}' " + ("is in another area" if role in seen else "is not an auth role")
                )
        if not own:
            notes.append(f"{where}left out (no roles of its own)")
            continue
        seen.update(own)
        out["areas"].append(
            {
                "id": area.get("id"),
                "label": area.get("label") or area.get("id"),
                "roles": own,
                **_layout(area, entities, notes, where),
            }
        )
    for role in roles:
        if out["areas"] and role not in seen:
            notes.append(f"role '{role}' is in no area; it gets the app's first layout")
    for look in brief.get("looks") or []:
        recipe = look.get("recipe")
        if recipe in RECIPES and all(recipe != kept["recipe"] for kept in out["looks"]):
            out["looks"].append({"recipe": recipe, "reason": look.get("reason") or ""})
    for recipe in ("minimal", "glass", "brutalist"):
        if len(out["looks"]) < 3 and all(recipe != kept["recipe"] for kept in out["looks"]):
            out["looks"].append({"recipe": recipe, "reason": "added by code (the brief had fewer than three looks)"})
            notes.append(f"look '{recipe}' added by code")
    return out, notes


# ---- build ------------------------------------------------------------------------------------------------------


def inject(project: Path, design: dict[str, Any]) -> None:
    """The prototype overlay into a scaffolded app: presentation only (shell, list views, recipes)."""
    app_dir = project / "src" / "components" / "app"
    for name in ("design.ts", "ProtoViews.tsx", "ProtoShell.tsx"):
        shutil.copy(HERE / "overlay" / name, app_dir / name)
    shutil.copy(HERE / "overlay" / "SiteShell.tsx", project / "src" / "components" / "layout" / "SiteShell.tsx")
    (project / "src" / "content" / "design.json").write_text(json.dumps(design, indent=2, ensure_ascii=False))
    globals_css = project / "src" / "app" / "globals.css"
    globals_css.write_text(globals_css.read_text() + (HERE / "overlay" / "recipes.css").read_text())
    app_list = app_dir / "AppList.tsx"
    source = app_list.read_text()
    rows = "<Rows section={section} entity={entity} records={records} />"
    anchor = 'import { RowActions } from "./RecordActions";'
    assert rows in source and anchor in source, "AppList.tsx changed: update the prototype's patch"
    source = source.replace(rows, "<ProtoRows Kit={Rows} section={section} entity={entity} records={records} />")
    source = source.replace(anchor, f'{anchor}\nimport {{ ProtoRows }} from "./ProtoViews";')
    app_list.write_text(source)


def shot_routes(spec: dict[str, Any], contract: dict[str, Any], main: str) -> dict[str, str]:
    from scripts.design_check_app import screen_routes

    routes = {"home": "/"}
    entity = (spec.get("app") or {}).get("entities", {}).get(main) or {}
    plural_route = None
    for page in spec["pages"]:
        sections = page.get("sections") or []
        if (
            "[" not in page["route"]
            and page["route"] != "/"
            and any(
                s.get("component") == "AppList" and (s.get("content") or {}).get("entity") == main for s in sections
            )
        ):
            plural_route = page["route"]
            break
    if plural_route:
        routes["list"] = plural_route
        for route in screen_routes(spec, contract):
            parts = route.strip("/").split("/")
            if route.startswith(f"{plural_route}/") and len(parts) == 2 and parts[1] not in ("new",):
                routes["detail"] = route
                break
    del entity
    return routes


GALLERY = ["glass", "aurora", "brutalist", "neon", "clay", "playful", "material", "soft"]


def gallery(looks: list[str]) -> list[str]:
    """Recipes the brief did not pick, to see them on the same layout (home and list, 1440 px, light)."""
    return [recipe for recipe in GALLERY if recipe not in looks][:6]


def area_plan(area: dict[str, Any], routes: dict[str, str], look: str) -> list[dict[str, Any]]:
    """Signed in as the area's first role: its home and main list, today's kit and the brief's first look."""
    views = []
    for key in ("home", "list"):
        if key not in routes:
            continue
        for variant, query in (("kit", "proto=off"), (look, f"look={look}")):
            for width in (1440, 375):
                name = f"area-{area['id']}-{key}-{variant}-{width}-light"
                url = f"{routes[key]}?{query}"
                views.append({"name": name, "route": url, "width": width, "scheme": "light", "role": area["roles"][0]})
    return views


def shot_plan(routes: dict[str, str], looks: list[str]) -> list[dict[str, Any]]:
    variants = [("kit", "proto=off"), *((look, f"look={look}") for look in looks)]
    views = []
    for key in ("home", "list"):
        if key in routes:
            for recipe in gallery(looks):
                url = f"{routes[key]}?look={recipe}"
                views.append({"name": f"{key}-g-{recipe}-1440-light", "route": url, "width": 1440, "scheme": "light"})
    for key, route in routes.items():
        for variant, query in variants:
            url = f"{route}{'&' if '?' in route else '?'}{query}"
            for width in (1440, 375):
                views.append(
                    {"name": f"{key}-{variant}-{width}-light", "route": url, "width": width, "scheme": "light"}
                )
            if key == "home" or (key == "list" and variant != "kit"):
                views.append({"name": f"{key}-{variant}-1440-dark", "route": url, "width": 1440, "scheme": "dark"})
    return views


async def build_one(name: str, out_dir: Path) -> dict[str, Any] | None:
    from scripts.site_check import BUILD_ROOT, DEV_INSTANCE
    from src.modules.shared.domain.backend_spec import validate_spec_data
    from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
    from src.orchestrator.backend.planner import build_plan
    from src.orchestrator.frontend.planner import plan_frontend
    from src.orchestrator.frontend.scaffold import scaffold_frontend
    from src.orchestrator.frontend.validation import FrontendValidationRequest, SandboxFrontendValidationRunner
    from src.orchestrator.integration.contract import build_contract
    from src.sandbox import DockerSandboxProvider, docker_sandbox

    docker_sandbox.instance_id = lambda: DEV_INSTANCE
    source = DRAFTS / name
    summary = json.loads((source / "draft.json").read_text())
    brief = json.loads((source / "design-brief.json").read_text())
    if not summary["ok"] or not brief:
        print(f"{name}: the draft is invalid or has no brief; run draft again")
        return None
    backend = validate_spec_data(json.loads((source / "backend-spec.json").read_text())).normalized
    design, notes = apply_design(brief, backend)
    contract = build_contract(backend, build_plan(backend))
    result = validate_frontend_spec_data(json.loads((source / "frontend-spec.json").read_text()))
    if not result.report.valid:
        print(f"{name}: FrontendSpec invalid: {[issue.message for issue in result.report.errors][:3]}")
        return None
    spec = result.normalized
    plan = plan_frontend(spec, contract)
    routes = shot_routes(spec, contract, design["mainEntity"])
    looks = [look["recipe"] for look in design["looks"]]
    target = BUILD_ROOT / f"proto-{uuid.uuid4().hex[:10]}"
    project = target / "frontend"
    scaffold_frontend(project, plan, spec, contract)
    inject(project, design)
    shutil.copy(HERE / "proto-shots.mjs", project / "proto-shots.mjs")
    views = shot_plan(routes, looks)
    area_routes: dict[str, dict[str, str]] = {}
    for area in design.get("areas") or []:
        area_routes[area["id"]] = shot_routes(spec, contract, area["mainEntity"])
        views += area_plan(area, area_routes[area["id"]], looks[0])
    (project / "shots.json").write_text(json.dumps(views))
    sandbox = DockerSandboxProvider().for_job(f"gen_PRO{uuid.uuid4().hex[:10].upper()}", project, "frontend")
    app_out = out_dir / name
    try:
        started = time.monotonic()
        outcome = await SandboxFrontendValidationRunner().run(
            FrontendValidationRequest(project=project, plan=plan, run_tests=False, sandbox=sandbox)
        )
        if outcome.summary.get("build") != "passed":
            print(f"{name}: build {outcome.summary}\n{outcome.digest[-4000:]}")
            return None
        print(f"  {name}: built in {time.monotonic() - started:.0f}s; screenshots")
        run = await sandbox.exec("node proto-shots.mjs shots shots.json", timeout_s=1200)
        if not (project / "shots" / "shots.json").is_file():
            print(f"{name}: screenshots failed\n{run.output[-3000:]}")
            return None
        shutil.rmtree(app_out, ignore_errors=True)
        shutil.copytree(project / "shots", app_out / "shots")
    finally:
        await sandbox.stop()
        shutil.rmtree(target, ignore_errors=True)
    report = {
        "name": name,
        "app": (spec.get("app") or {}).get("name") or name,
        "requirement": (REQUIREMENTS / f"{name}.md").read_text(),
        "draft": {k: summary[k] for k in ("seconds", "repairs", "costUsd", "archetypeCandidates", "productTypes")},
        "calls": [
            {k: c.get(k) for k in ("step", "prompt", "durationMs", "inputTokens", "outputTokens")}
            for c in summary["calls"]
        ],
        "brief": brief,
        "design": design,
        "replaced": notes,
        "draftNotes": [n.get("message") for n in summary.get("notes") or [] if isinstance(n, dict)],
        "routes": routes,
        "areaRoutes": area_routes,
        "looks": looks,
        "checks": outcome.summary,
        "entities": {e["name"]: [f["name"] for f in e.get("fields") or []] for e in backend.get("entities") or []},
    }
    (app_out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"{name}: {len(json.loads((app_out / 'shots' / 'shots.json').read_text()))} screenshots → {app_out}")
    return report


# ---- review page ------------------------------------------------------------------------------------------------


def _esc(text: Any) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def page(out_dir: Path) -> Path:
    reports = [json.loads(p.read_text()) for p in sorted(out_dir.glob("*/report.json"))]
    parts = [
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>",
        "<title>App design prototype</title><style>",
        ":root{color-scheme:light dark;--bg:#fafafa;--fg:#111;--muted:#666;--line:#ddd;--card:#fff}",
        "@media (prefers-color-scheme:dark){:root{--bg:#111;--fg:#eee;--muted:#999;--line:#333;--card:#1a1a1a}}",
        "body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg)}",
        "main{max-width:1800px;margin:auto;padding:24px 16px}h1{margin:0 0 4px}h2{margin:48px 0 8px;border-top:2px solid var(--fg);padding-top:16px}",  # noqa: E501
        ".muted{color:var(--muted)}.grid{display:grid;gap:12px;grid-template-columns:repeat(4,minmax(0,1fr));align-items:start}",
        ".grid.m{grid-template-columns:repeat(4,minmax(0,220px))}figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}",  # noqa: E501
        "figure img{width:100%;display:block}figcaption{padding:6px 10px;font-size:13px}figure a{display:block}",
        ".brief{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin:12px 0}",
        ".box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px}",
        "details{margin:8px 0}pre{white-space:pre-wrap;font-size:13px}h3{margin:24px 0 8px}code{font-size:13px}",
        "@media (max-width:900px){.grid{grid-template-columns:1fr 1fr}}</style><main>",
        "<h1>App design prototype (Story 23.0)</h1>",
        f"<p class='muted'>{date.today()} · real Gemini drafts with a design brief, built on the app kit with a "
        "prototype overlay, on the mock API. Columns: today's kit, then the brief's layout in each of its three looks. "
        "Click a screenshot for full size.</p>",
    ]
    for r in reports:
        d = r["design"]
        views = ", ".join(f"{e}: <b>{v['view']}</b>" for e, v in d["entities"].items())
        roles = "<br>".join(
            f"{e}: " + ", ".join(f"{k}={'/'.join(v) if isinstance(v, list) else v}" for k, v in x["roles"].items())
            for e, x in d["entities"].items()
        )
        looks = "".join(f"<li><b>{_esc(look['recipe'])}</b>: {_esc(look['reason'])}</li>" for look in d["looks"])
        replaced = "".join(f"<li>{_esc(n)}</li>" for n in r["replaced"]) or "<li>nothing</li>"
        calls = ", ".join(
            f"{c['step']} {round((c['durationMs'] or 0) / 1000)}s ({c['inputTokens']}→{c['outputTokens']} tokens)"
            for c in r["calls"]
        )
        parts += [
            f"<h2>{_esc(r['app'])} <span class='muted'>({_esc(r['name'])})</span></h2>",
            f"<details><summary>Requirement</summary><pre>{_esc(r['requirement'])}</pre></details>",
            "<div class='brief'>",
            f"<div class='box'><b>Brief</b><br>archetype <b>{d['archetype']}</b> · shell <b>{d['shell']}</b> · "
            f"mobile <b>{d['mobileNav']}</b> · home <b>{d['homeView']}</b> · main <b>{d['mainEntity']}</b>"
            f"<br>{views}<p class='muted'>{_esc(d['reason'])}</p></div>",
            f"<div class='box'><b>Field roles</b><br><small>{roles}</small></div>",
            f"<div class='box'><b>Looks</b><ul>{looks}</ul></div>",
            f"<div class='box'><b>Replaced by code</b><ul>{replaced}</ul><small class='muted'>Draft: {calls}; "
            f"{r['draft']['repairs']} repair(s); ${r['draft']['costUsd']}. Code ranked: "
            f"{', '.join(r['draft']['archetypeCandidates'])} ({_esc(', '.join(r['draft']['productTypes']))})</small></div>",  # noqa: E501
            "</div>",
        ]
        variants = ["kit", *r["looks"]]
        labels = {"kit": "Today's kit", **{look: f"Brief · {look}" for look in r["looks"]}}
        shots = set(json.loads((out_dir / r["name"] / "shots" / "shots.json").read_text()))
        for key in r["routes"]:
            for width, suffix in ((1440, "light"), (1440, "dark"), (375, "light")):
                names = [f"{key}-{v}-{width}-{suffix}" for v in variants]
                if not any(n in shots for n in names):
                    continue
                parts.append(
                    f"<h3>{key} <span class='muted'>({_esc(r['routes'][key])}) · {width} px · {suffix}</span></h3>"
                )
                parts.append(f"<div class='grid{' m' if width < 600 else ''}'>")
                for variant, shot in zip(variants, names, strict=True):
                    if shot in shots:
                        src = f"{r['name']}/shots/{shot}.png"
                        parts.append(
                            f"<figure><a href='{src}'><img src='{src}' loading='lazy' alt=''></a>"
                            f"<figcaption>{_esc(labels[variant])}</figcaption></figure>"
                        )
                    else:
                        parts.append("<figure><figcaption class='muted'>(none)</figcaption></figure>")
                parts.append("</div>")
        areas = r["design"].get("areas") or []
        if areas:
            parts.append(
                "<h3>Areas: the same app signed in as each role</h3><p class='muted'>Prototype: the area follows the "
                "signed-in role at run time (Story 23.10 gives each area its own routes). Columns: today's kit as that "
                f"role, then the area's layout in the first look ({_esc(r['looks'][0])}).</p>"
            )
            for area in areas:
                views = ", ".join(f"{e}: <b>{v['view']}</b>" for e, v in area["entities"].items())
                parts.append(
                    f"<div class='box'><b>{_esc(area['label'])}</b> (roles: {_esc(', '.join(area['roles']))}) · "
                    f"{area['archetype']} · shell <b>{area['shell']}</b> · mobile <b>{area['mobileNav']}</b> · home "
                    f"<b>{area['homeView']}</b> · main <b>{area['mainEntity']}</b><br>{views}</div>"
                )
                for key in ("home", "list"):
                    cells = []
                    for width in (1440, 375):
                        for variant in ("kit", r["looks"][0]):
                            name = f"area-{area['id']}-{key}-{variant}-{width}-light"
                            if name in shots:
                                src = f"{r['name']}/shots/{name}.png"
                                label = f"{'Today' if variant == 'kit' else 'Area layout'} · {width}px"
                                cells.append(
                                    f"<figure><a href='{src}'><img src='{src}' loading='lazy' alt=''></a>"
                                    f"<figcaption>{label}</figcaption></figure>"
                                )
                    if cells:
                        parts.append(f"<h3>{_esc(area['label'])} · {key}</h3><div class='grid'>{''.join(cells)}</div>")
        for key in ("home", "list"):
            names = [(recipe, f"{key}-g-{recipe}-1440-light") for recipe in gallery(r["looks"])]
            names = [(recipe, name) for recipe, name in names if name in shots]
            if names:
                parts.append(f"<h3>More recipes the brief did not pick · {key} · 1440 px</h3><div class='grid'>")
                for recipe, name in names:
                    src = f"{r['name']}/shots/{name}.png"
                    parts.append(
                        f"<figure><a href='{src}'><img src='{src}' loading='lazy' alt=''></a>"
                        f"<figcaption>Same layout · {recipe}</figcaption></figure>"
                    )
                parts.append("</div>")
    parts.append("</main></html>")
    path = out_dir / "index.html"
    path.write_text("\n".join(parts))
    return path


def check(names: list[str]) -> None:
    """No model call: the archetype candidates, the answer schema and the rendered prompt's size per requirement."""
    from src.engines.prompts import PromptLibrary
    from src.modules.shared.domain.entities import SpecDraftEntity
    from src.modules.shared.domain.enums import GenerationMode, SpecSource
    from src.orchestrator.drafting.answer_schema import app_answer_schema
    from src.orchestrator.drafting.drafts import inline_inputs, write_inputs

    schema = with_design(app_answer_schema("backend-spec.json", "app-outline.json", "notes.json"))
    print(
        f"answer schema: {len(json.dumps(schema))} chars, design in outline: {'design' in schema['$defs']['AppOutline']['properties']}"  # noqa: E501
    )
    for name in names:
        requirement = (REQUIREMENTS / f"{name}.md").read_text()
        candidates, products = archetype_candidates(requirement)
        work = OUT / "check" / name
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        draft = SpecDraftEntity(
            owner_id=uuid.uuid4(),
            source=SpecSource.REQUIREMENT,
            mode=GenerationMode.DYNAMIC,
            requirement_text=requirement,
            requirement_format="markdown",
            engine="gemini_api",
        )
        context = write_inputs(work, draft, REPO / "examples", None, None, app=True)
        context["inline"] = True
        context |= inline_inputs(work, context) | {"archetype_candidates": ", ".join(candidates)}
        text = PromptLibrary(HERE / "prompts").render("draft_app", "v3proto", **context).text
        (work / "prompt.md").write_text(text)
        print(f"{name}: candidates {candidates} from {products}; prompt {len(text)} chars → {work / 'prompt.md'}")


async def main(args: argparse.Namespace) -> None:
    names = args.app or sorted(p.stem for p in REQUIREMENTS.glob("*.md"))
    if args.step == "check":
        check(names)
        return
    if args.step == "draft":
        for name in names:  # one at a time: three paid calls, each printed as it ends
            await draft_one(name)
        return
    out_dir = OUT / str(date.today())
    if args.step == "build":
        for name in names:
            await build_one(name, out_dir)
    print(f"review page → {page(out_dir)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["check", "draft", "build", "page"])
    parser.add_argument("--app", action="append", help="a requirement name (default: all)")
    asyncio.run(main(parser.parse_args()))
