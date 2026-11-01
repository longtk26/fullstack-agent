"""fastapi-skills conventions checker (Story 6.2, check `conventions`). Static analysis only: never imports the code.

Each violation quotes the skill rule it breaks, so the repair prompt can fix it without guessing.
"""

import ast
from pathlib import Path
from typing import Any

from src.orchestrator.scaffold import changed_owned

ENTITIES_DIR = "src/modules/shared/domain/entities"
MODELS_DIR = "src/modules/shared/infrastructure/models"
ORM_MODULES = ("sqlmodel", "sqlalchemy")

RULES = {
    "entity_pure": "Domain entities are pure Pydantic BaseModel without any ORM annotations.",
    "usecase_no_orm": "Use cases depend ONLY on output port interfaces, never concrete repositories or ORM models.",
    "usecase_transactional": "Write operations in use cases must be decorated with @Transactional.",
    "no_http_exception": "Do NOT throw raw HTTPException inside use cases; raise BaseException subclasses.",
    "model_registered": "All ORM models must be imported in src/modules/__init__.py so Alembic can discover them.",
    "router_registered": "All feature routers must be registered in src/routers.py (all_router).",
    "repo_dep": "Repositories export I<Name>RepoDep = Annotated[I<Name>Repository, Depends(<Name>Repository)].",
    "usecase_dep": "Use cases export <Action>UsecaseDep = Annotated[<Action>Usecase, Depends(<Action>Usecase)].",
    "dto_to_entity": "Request DTOs define a .to_entity() converter method.",
    "rate_limiter": "Protect API endpoints with rate limiting (slowapi limiter wired in src/main.py).",
    "owned_file": "Generator-owned files must not be edited (src/libs, src/configs, src/main.py, alembic/env.py, ...).",
    "planned_file": "Implement exactly the planned files (.bga/plan.json).",
}


def _violation(file: str, line: int, rule: str, detail: str) -> dict[str, Any]:
    return {"file": file, "line": line, "rule": rule, "message": detail, "hint": RULES[rule]}


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(errors="replace"))
    except (SyntaxError, ValueError):
        return None  # reported by the syntax check


def _imports(tree: ast.Module) -> list[tuple[int, str]]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.lineno, node.module))
            found.extend((node.lineno, f"{node.module}.{alias.name}") for alias in node.names)
    return found


def _imported_names(tree: ast.Module) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
    return names


def _assigned_names(tree: ast.Module) -> set[str]:
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _decorator_names(function: ast.AST) -> set[str]:
    names = set()
    for decorator in getattr(function, "decorator_list", []):
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _rel(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


def check_conventions(project: Path, plan: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []

    # Domain entities: no ORM imports.
    for path in sorted((project / ENTITIES_DIR).glob("*.py")):
        tree = _parse(path)
        for line, module in _imports(tree) if tree else []:
            if module.split(".")[0] in ORM_MODULES:
                violations.append(_violation(_rel(project, path), line, "entity_pure", f"imports {module}"))

    for module in plan.get("modules", []):
        # Planned files exist.
        expected = [
            module["port"]["file"],
            module["port"]["implementationFile"],
            module["router"]["file"],
            *(usecase["file"] for usecase in module["usecases"]),
        ]
        for relative in expected:
            if not (project / relative).is_file():
                violations.append(_violation(relative, 0, "planned_file", "planned file is missing"))

        # Repository exports its Dep alias.
        impl = project / module["port"]["implementationFile"]
        tree = _parse(impl) if impl.is_file() else None
        if tree is not None and module["port"]["dep"] not in _assigned_names(tree):
            violations.append(_violation(_rel(project, impl), 0, "repo_dep", f"{module['port']['dep']} is not defined"))

        # Use cases: Dep alias, no ORM / concrete repo imports, @Transactional on writes, no HTTPException.
        for usecase in module["usecases"]:
            path = project / usecase["file"]
            tree = _parse(path) if path.is_file() else None
            if tree is None:
                continue
            relative = _rel(project, path)
            if usecase["dep"] not in _assigned_names(tree):
                violations.append(_violation(relative, 0, "usecase_dep", f"{usecase['dep']} is not defined"))
            for line, imported in _imports(tree):
                if imported.split(".")[0] in ORM_MODULES or ".infrastructure." in f".{imported}.":
                    violations.append(_violation(relative, line, "usecase_no_orm", f"imports {imported}"))
                if imported.endswith("HTTPException"):
                    violations.append(_violation(relative, line, "no_http_exception", f"imports {imported}"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Raise) and node.exc is not None:
                    target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
                    if isinstance(target, ast.Name) and target.id == "HTTPException":
                        violations.append(
                            _violation(relative, node.lineno, "no_http_exception", "raises HTTPException")
                        )
            if usecase["transactional"]:
                classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == usecase["class"]]
                methods = [m for c in classes for m in c.body if isinstance(m, ast.FunctionDef | ast.AsyncFunctionDef)]
                if classes and not any("Transactional" in _decorator_names(m) for m in methods):
                    violations.append(
                        _violation(relative, classes[0].lineno, "usecase_transactional", f"{usecase['class']} writes")
                    )

        # Request DTOs have to_entity().
        dto_classes: dict[str, ast.ClassDef] = {}
        for relative in module["dtoFiles"]:
            path = project / relative
            tree = _parse(path) if path.is_file() else None
            for node in tree.body if tree else []:
                if isinstance(node, ast.ClassDef):
                    dto_classes[node.name] = node
        for op in module["operations"]:
            name = op.get("requestDto")
            if not name:
                continue
            node = dto_classes.get(name)
            if node is None:
                violations.append(_violation(module["dtoFiles"][0], 0, "planned_file", f"{name} is not defined"))
            elif not any(isinstance(m, ast.FunctionDef) and m.name == "to_entity" for m in node.body):
                violations.append(_violation(module["dtoFiles"][0], node.lineno, "dto_to_entity", f"{name}"))

    # Models registered in src/modules/__init__.py.
    registry = project / "src/modules/__init__.py"
    registry_tree = _parse(registry) if registry.is_file() else None
    registered = _imported_names(registry_tree) if registry_tree else set()
    for model in plan.get("models", []):
        if model["class"] not in registered:
            violations.append(
                _violation("src/modules/__init__.py", 0, "model_registered", f"{model['class']} is not imported")
            )

    # Routers registered.
    routers = project / "src/routers.py"
    routers_tree = _parse(routers) if routers.is_file() else None
    router_names = (
        {n.id for n in ast.walk(routers_tree) if isinstance(n, ast.Name)} if routers_tree is not None else set()
    )
    for module in plan.get("modules", []):
        if module["router"]["variable"] not in router_names:
            violations.append(
                _violation("src/routers.py", 0, "router_registered", f"{module['router']['variable']} missing")
            )

    main = project / "src/main.py"
    if not main.is_file() or "SlowAPIMiddleware" not in main.read_text(errors="replace"):
        violations.append(_violation("src/main.py", 0, "rate_limiter", "SlowAPIMiddleware is not attached"))

    for relative in changed_owned(project):
        if relative.startswith("src/modules/"):
            continue
        violations.append(_violation(relative, 0, "owned_file", "changed after the scaffold"))
    return violations
