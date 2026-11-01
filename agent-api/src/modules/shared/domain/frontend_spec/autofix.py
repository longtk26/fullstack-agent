"""Autofix for drafted FrontendSpec (Story 18.3).

Repairs common drafting mistakes deterministically before invoking an engine repair loop.
"""

from typing import Any

from .normalizer import page_id, route_params


def _iter_all_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        result.append(section)
        children = section.get("children")
        if isinstance(children, list):
            result.extend(_iter_all_sections(children))
    return result


def _page_entity(page: dict[str, Any]) -> str | None:
    for section in _iter_all_sections(page.get("sections") or []):
        data = section.get("data")
        if isinstance(data, dict):
            op = data.get("operationId")
            if isinstance(op, str) and "." in op:
                return op.split(".", 1)[0]
            col = data.get("collection")
            if isinstance(col, str) and col:
                return col
    return None


def _find_prefix_page(pages: list[dict[str, Any]], target_route: str) -> dict[str, Any] | None:
    candidates = []
    target_clean = target_route.rstrip("/") + "/"
    for p in pages:
        p_route = p.get("route", "")
        if route_params(p_route) or p_route in ("", "/"):
            continue
        p_clean = p_route.rstrip("/") + "/"
        if target_clean.startswith(p_clean):
            candidates.append((len(p_route), p))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
    return None


def _find_list_page_for_entity(pages: list[dict[str, Any]], entity: str) -> dict[str, Any] | None:
    for p in pages:
        if route_params(p.get("route", "")):
            continue
        for section in _iter_all_sections(p.get("sections") or []):
            data = section.get("data")
            if isinstance(data, dict):
                op = data.get("operationId")
                col = data.get("collection")
                if isinstance(op, str) and "." in op:
                    op_entity, op_action = op.split(".", 1)
                    if op_entity == entity and (op_action in ("list", "all", "find") or data.get("action") == "list"):
                        return p
                if isinstance(col, str) and col == entity:
                    return p
    return None


def autofix_frontend_spec(spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Inspects `spec` for links targeting pages with unbound route parameters (FE_ROUTE_PARAM_UNBOUND),
    points them at the nearest prefix page or list page for the same entity, or removes them if optional.
    Returns `(fixed_spec, notes)` where notes are assumption entries."""
    pages = [p for p in spec.get("pages") or [] if isinstance(p, dict)]
    pages_by_id = {p.get("id") or page_id(p.get("route", "")): p for p in pages}
    notes: list[dict[str, Any]] = []

    def resolve_target(
        target_id: str, provided_params: set[str] | None = None
    ) -> tuple[dict[str, Any] | None, list[str]]:
        target_page = pages_by_id.get(target_id)
        if not target_page:
            return None, []
        params = route_params(target_page.get("route", ""))
        if not params:
            return None, []
        if provided_params and set(params).issubset(provided_params):
            return None, []
        # Target needs route params!
        target_route = target_page.get("route", "")
        prefix = _find_prefix_page(pages, target_route)
        if prefix:
            return prefix, params
        entity = _page_entity(target_page)
        if entity:
            list_page = _find_list_page_for_entity(pages, entity)
            if list_page:
                return list_page, params
        return None, params

    def make_note(
        path: str,
        target_id: str,
        target_route: str,
        params: list[str],
        candidate: dict[str, Any] | None,
    ) -> dict[str, Any]:
        param_str = ", ".join(f"[{p}]" for p in params)
        if candidate:
            cand_id = candidate.get("id") or page_id(candidate.get("route", ""))
            cand_route = candidate.get("route", "")
            msg = (
                f"Link to '{target_id}' ({target_route}) now points to '{cand_id}' ({cand_route}): "
                f"a link cannot fill {param_str}"
            )
        else:
            msg = f"Link to '{target_id}' ({target_route}) was removed: a link cannot fill {param_str}"
        return {"spec": "frontend", "path": path, "message": msg, "suggestion": None}

    # 1. layout.header.navigation
    layout = spec.get("layout")
    if isinstance(layout, dict):
        header = layout.get("header")
        if isinstance(header, dict) and isinstance(header.get("navigation"), list):
            new_nav = []
            for idx, item in enumerate(header["navigation"]):
                if isinstance(item, dict) and isinstance(item.get("page"), str):
                    cand, params = resolve_target(item["page"])
                    if params:
                        target_id = item["page"]
                        target_route = pages_by_id[target_id].get("route", "")
                        if cand:
                            cand_id = cand.get("id") or page_id(cand.get("route", ""))
                            item["page"] = cand_id
                            notes.append(
                                make_note(
                                    f"/layout/header/navigation/{idx}/page", target_id, target_route, params, cand
                                )
                            )
                            new_nav.append(item)
                        else:
                            notes.append(
                                make_note(f"/layout/header/navigation/{idx}", target_id, target_route, params, None)
                            )
                    else:
                        new_nav.append(item)
                else:
                    new_nav.append(item)
            header["navigation"] = new_nav

        # 2. layout.footer.links
        footer = layout.get("footer")
        if isinstance(footer, dict) and isinstance(footer.get("links"), list):
            new_links = []
            for idx, item in enumerate(footer["links"]):
                if isinstance(item, dict) and isinstance(item.get("page"), str):
                    cand, params = resolve_target(item["page"])
                    if params:
                        target_id = item["page"]
                        target_route = pages_by_id[target_id].get("route", "")
                        if cand:
                            cand_id = cand.get("id") or page_id(cand.get("route", ""))
                            item["page"] = cand_id
                            notes.append(
                                make_note(f"/layout/footer/links/{idx}/page", target_id, target_route, params, cand)
                            )
                            new_links.append(item)
                        else:
                            notes.append(
                                make_note(f"/layout/footer/links/{idx}", target_id, target_route, params, None)
                            )
                    else:
                        new_links.append(item)
                else:
                    new_links.append(item)
            footer["links"] = new_links

    # 3. Section content
    def fix_content(container: Any, path: str) -> None:
        if isinstance(container, dict):
            # Check keys
            keys_to_delete = []
            for key, val in list(container.items()):
                subpath = f"{path}/{key}"
                if key == "page" and isinstance(val, str):
                    cand, params = resolve_target(val)
                    if params:
                        target_id = val
                        target_route = pages_by_id[target_id].get("route", "")
                        if cand:
                            cand_id = cand.get("id") or page_id(cand.get("route", ""))
                            container["page"] = cand_id
                            notes.append(make_note(subpath, target_id, target_route, params, cand))
                elif isinstance(val, dict):
                    if "page" in val and isinstance(val["page"], str):
                        provided = set((val.get("params") or {}).keys())
                        cand, params = resolve_target(val["page"], provided)
                        if params:
                            target_id = val["page"]
                            target_route = pages_by_id[target_id].get("route", "")
                            if cand:
                                cand_id = cand.get("id") or page_id(cand.get("route", ""))
                                val["page"] = cand_id
                                notes.append(make_note(f"{subpath}/page", target_id, target_route, params, cand))
                            elif key in ("cta", "secondary_cta", "link"):
                                keys_to_delete.append((key, target_id, target_route, params))
                            continue
                    fix_content(val, subpath)
                elif isinstance(val, list):
                    fix_content(val, subpath)
            for k, target_id, target_route, params in keys_to_delete:
                del container[k]
                notes.append(make_note(f"{path}/{k}", target_id, target_route, params, None))

        elif isinstance(container, list):
            items_to_remove = []
            for idx, item in enumerate(container):
                subpath = f"{path}/{idx}"
                if isinstance(item, dict):
                    if "page" in item and isinstance(item["page"], str):
                        provided = set((item.get("params") or {}).keys())
                        cand, params = resolve_target(item["page"], provided)
                        if params:
                            target_id = item["page"]
                            target_route = pages_by_id[target_id].get("route", "")
                            if cand:
                                cand_id = cand.get("id") or page_id(cand.get("route", ""))
                                item["page"] = cand_id
                                notes.append(make_note(f"{subpath}/page", target_id, target_route, params, cand))
                            else:
                                items_to_remove.append((item, target_id, target_route, params, subpath))
                            continue
                    fix_content(item, subpath)
            for item, target_id, target_route, params, subpath in items_to_remove:
                container.remove(item)
                notes.append(make_note(subpath, target_id, target_route, params, None))

    for p_idx, page in enumerate(pages):
        for s_idx, section in enumerate(page.get("sections") or []):
            if isinstance(section, dict) and "content" in section:
                fix_content(section["content"], f"/pages/{p_idx}/sections/{s_idx}/content")

    _autofix_journeys(spec, pages, pages_by_id, notes)

    return spec, notes


def _autofix_journeys(
    spec: dict[str, Any],
    pages: list[dict[str, Any]],
    pages_by_id: dict[str, Any],
    notes: list[dict[str, Any]],
) -> None:
    journeys = spec.get("journeys")
    if not isinstance(journeys, list):
        return

    all_sections = _iter_all_sections([s for p in pages for s in (p.get("sections") or []) if isinstance(s, dict)])
    sections_by_id = {sec["id"]: sec for sec in all_sections if isinstance(sec.get("id"), str)}
    forms_by_id = {f["id"]: f for f in spec.get("forms") or [] if isinstance(f, dict) and isinstance(f.get("id"), str)}

    clean_journeys = []
    for j_idx, journey in enumerate(journeys):
        if not isinstance(journey, dict):
            continue
        steps = journey.get("steps")
        if not isinstance(steps, list):
            continue

        clean_steps = []
        last_section: str | None = None
        last_page: str | None = None

        for s_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            do = step.get("do")
            if do not in ("visit", "open", "submit", "action", "expect"):
                continue

            step_path = f"/journeys/{j_idx}/steps/{s_idx}"

            if do == "visit":
                page = step.get("page")
                if not page or page not in pages_by_id:
                    target = next((p for p in pages if p.get("route") == page or p.get("route") == f"/{page}"), None)
                    if target:
                        step["page"] = target.get("id") or page_id(target.get("route", ""))
                        page = step["page"]
                if page and page in pages_by_id:
                    last_page = page
                    clean_steps.append(step)
                    p_secs = pages_by_id[page].get("sections") or []
                    if p_secs and isinstance(p_secs[0], dict) and p_secs[0].get("id"):
                        last_section = p_secs[0]["id"]
                else:
                    notes.append(
                        {
                            "spec": "frontend",
                            "path": f"{step_path}/page",
                            "message": f"Dropped visit step to unknown page '{page}'",
                            "suggestion": None,
                        }
                    )

            elif do == "open":
                sec_id = step.get("section") or last_section
                if sec_id and sec_id in sections_by_id:
                    step["section"] = sec_id
                    last_section = sec_id
                    clean_steps.append(step)
                else:
                    notes.append(
                        {
                            "spec": "frontend",
                            "path": f"{step_path}/section",
                            "message": f"Dropped open step on invalid section '{sec_id}'",
                            "suggestion": None,
                        }
                    )

            elif do == "submit":
                sec_id = step.get("section") or last_section
                if sec_id and sec_id in sections_by_id:
                    sec = sections_by_id[sec_id]
                    form_id = sec.get("form")
                    form = forms_by_id.get(form_id) if form_id else None
                    if form is not None or sec.get("component") == "Form":
                        step["section"] = sec_id
                        last_section = sec_id
                        if form is not None and isinstance(step.get("values"), dict):
                            valid_fields = {
                                f["name"] for f in form.get("fields") or [] if isinstance(f, dict) and "name" in f
                            }
                            step["values"] = {k: v for k, v in step["values"].items() if k in valid_fields}
                        clean_steps.append(step)
                    else:
                        notes.append(
                            {
                                "spec": "frontend",
                                "path": f"{step_path}/section",
                                "message": f"Dropped submit step on non-form section '{sec_id}'",
                                "suggestion": None,
                            }
                        )
                else:
                    notes.append(
                        {
                            "spec": "frontend",
                            "path": f"{step_path}/section",
                            "message": f"Dropped submit step on unknown section '{sec_id}'",
                            "suggestion": None,
                        }
                    )

            elif do == "action":
                sec_id = step.get("section") or last_section
                if sec_id and sec_id in sections_by_id:
                    sec = sections_by_id[sec_id]
                    content = sec.get("content") or {}
                    actions = content.get("actions") or []
                    action_ids = [act["id"] for act in actions if isinstance(act, dict) and "id" in act]
                    act_id = step.get("action")
                    if not act_id and action_ids:
                        act_id = action_ids[0]
                        step["action"] = act_id
                        notes.append(
                            {
                                "spec": "frontend",
                                "path": f"{step_path}/action",
                                "message": f"Filled action '{act_id}' for section '{sec_id}'",
                                "suggestion": None,
                            }
                        )
                    if act_id and act_id in action_ids:
                        step["section"] = sec_id
                        last_section = sec_id
                        clean_steps.append(step)
                    else:
                        notes.append(
                            {
                                "spec": "frontend",
                                "path": step_path,
                                "message": f"Dropped action step on section '{sec_id}' without valid action",
                                "suggestion": None,
                            }
                        )
                else:
                    notes.append(
                        {
                            "spec": "frontend",
                            "path": f"{step_path}/section",
                            "message": f"Dropped action step on unknown section '{sec_id}'",
                            "suggestion": None,
                        }
                    )

            elif do == "expect":
                sec_id = step.get("section") or last_section
                if not sec_id and last_page and last_page in pages_by_id:
                    p_secs = pages_by_id[last_page].get("sections") or []
                    if p_secs and isinstance(p_secs[0], dict) and p_secs[0].get("id"):
                        sec_id = p_secs[0]["id"]
                if sec_id and sec_id in sections_by_id:
                    if step.get("text") is not None or step.get("count") is not None or step.get("changed") is not None:
                        step["section"] = sec_id
                        last_section = sec_id
                        clean_steps.append(step)
                    else:
                        notes.append(
                            {
                                "spec": "frontend",
                                "path": step_path,
                                "message": "Dropped expect step missing text/count/changed",
                                "suggestion": None,
                            }
                        )
                else:
                    notes.append(
                        {
                            "spec": "frontend",
                            "path": f"{step_path}/section",
                            "message": f"Dropped expect step on unknown section '{sec_id}'",
                            "suggestion": None,
                        }
                    )

        if clean_steps:
            journey["steps"] = clean_steps
            clean_journeys.append(journey)
        else:
            j_id = journey.get("id") or str(j_idx)
            notes.append(
                {
                    "spec": "frontend",
                    "path": f"/journeys/{j_idx}",
                    "message": f"Dropped journey '{j_id}' because all steps were invalid",
                    "suggestion": None,
                }
            )

    spec["journeys"] = clean_journeys
