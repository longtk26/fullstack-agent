"""Backend CRUD from templates (Story 17.6). No LLM.

The architecture plan (`planner.py`) fixes every name, file, column, operation and test case of a fastapi-skills
backend; for the CRUD parts this module writes them directly, in the shape of the golden projects
(`src/engines/golden/two_entity`, `shop`):

    database   src/modules/shared/domain/entities/<entity>_entity.py (+ enums), .../models/<entity>_model.py,
               both packages' __init__.py and src/modules/__init__.py (models registered for Alembic)
    module     ports/output (interface + Dep re-export), infrastructure/persistence (repository + `I<Name>RepoDep`),
               one use case per operation (+ `Dep`), request / response / list DTOs, the router; src/routers.py
    tests      tests/modules/<module>/test_<entity>_api.py: one test per planned case; records are inserted with
               the ORM, so entities without a create endpoint are testable too

Output is a pure function of (spec, plan): byte-identical between runs. The sandbox's ruff normalizes it once
(`generate_database` / `generate_backend`), after which the files are recorded as generator-owned. What is not CRUD
(custom operations, business rules, auth and policies) is left to the engine: `codegen_gaps` says why per module.
"""

import json
import keyword
import re
import sys
from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_snake

from .contract import _request_columns, _required

ENTITIES_PKG = "src/modules/shared/domain/entities"
MODELS_PKG = "src/modules/shared/infrastructure/models"
CRUD_ACTIONS = ("create", "get", "list", "update", "delete")
RESERVED = {"usecase", "q", "sort", "limit", "offset", "body", "id"}
FOREIGN_KEY_VIOLATION = "23503"

# -- what the templates cover ------------------------------------------------------------------------------------------


def database_gaps(plan: dict[str, Any]) -> list[str]:
    """Why the models cannot be generated (empty: they can)."""
    gaps = []
    for model in plan["models"]:
        for relation in model.get("relationships", []):
            if relation.get("type") not in ("one-to-many", None) or relation.get("link"):
                gaps.append(f"{model['entity']}.{relation['attr']}: {relation.get('type')} relationships")
    if plan.get("linkModels"):
        gaps.append("many-to-many link models")
    return sorted(set(gaps))


def is_crud(op: dict[str, Any]) -> bool:
    return op.get("type") == "crud" and op.get("action") in CRUD_ACTIONS


def codegen_gaps(module: dict[str, Any]) -> list[str]:
    """What the engine still writes in a module (empty: the templates write all of it)."""
    gaps = []
    for op in module["operations"]:
        where = op["operationId"]
        if not is_crud(op):
            gaps.append(f"{where}: custom operation")
        if op.get("rules"):
            gaps.append(f"{where}: business rules")
        if op.get("auth"):
            gaps.append(f"{where}: auth / policy")
    return gaps


# -- helpers -----------------------------------------------------------------------------------------------------------


class Imports:
    """`import x` / `from a import b` lines in isort order: stdlib, third party, first party (src)."""

    def __init__(self) -> None:
        self.modules: set[str] = set()
        self.names: dict[str, set[str]] = {}

    def add(self, module: str, *names: str) -> "Imports":
        if names:
            self.names.setdefault(module, set()).update(names)
        else:
            self.modules.add(module)
        return self

    def render(self) -> str:
        groups: list[list[str]] = [[], [], []]
        for module in self.modules:
            groups[self._group(module)].append((f"import {module}", module))
        for module, names in self.names.items():
            ordered = sorted(names, key=lambda name: (not name.isupper() or len(name) == 1, name.lower(), name))
            line = f"from {module} import {', '.join(ordered)}"
            if len(line) > 120:
                line = f"from {module} import (\n" + "".join(f"    {name},\n" for name in ordered) + ")"
            groups[self._group(module)].append((line, module))
        blocks = []
        for group in groups:
            lines = [line for line, _ in sorted(group, key=lambda item: (item[0].startswith("from "), item[1]))]
            if lines:
                blocks.append("\n".join(lines))
        return "\n\n".join(blocks) + "\n" if blocks else ""

    @staticmethod
    def _group(module: str) -> int:
        root = module.split()[0].split(".")[0]
        if root in sys.stdlib_module_names:
            return 0
        return 2 if root in ("src", "tests") or module.startswith(".") else 1


def _py(value: Any) -> str:
    """A Python literal for a JSON value."""
    if value is None or isinstance(value, bool):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return repr(value)


def _member(value: str) -> str:
    name = re.sub(r"\W+", "_", str(value)).strip("_").upper() or "VALUE"
    if name[0].isdigit() or keyword.iskeyword(name.lower()):
        name = f"V_{name}"
    return name


def _type(column: dict[str, Any], imports: Imports, response: bool = False) -> str:
    kind = column["type"]
    if kind == "enum":
        return column["enum"]["class"]
    if kind == "uuid":
        imports.add("uuid")
        return "uuid.UUID"
    if kind == "decimal":
        if response:
            return "float"
        imports.add("decimal", "Decimal")
        return "Decimal"
    if kind == "date":
        if column.get("attr") == "date":
            imports.add("datetime as dt")
            return "dt.date"
        imports.add("datetime", "date")
        return "date"
    if kind == "datetime":
        if column.get("attr") == "datetime":
            imports.add("datetime as dt")
            return "dt.datetime"
        imports.add("datetime", "datetime")
        return "datetime"
    if kind == "json":
        imports.add("typing", "Any")
        return "dict[str, Any]"
    return {"string": "str", "text": "str", "integer": "int", "float": "float", "boolean": "bool"}[kind]


def _default(column: dict[str, Any]) -> dict[str, Any]:
    return column.get("default") or {}


def _value(column: dict[str, Any], value: Any) -> str:
    if column["type"] == "enum":
        return f"{column['enum']['class']}.{_member(value)}"
    if column["type"] == "decimal":
        return f'Decimal("{value}")'
    return _py(value)


def _enums(model: dict[str, Any]) -> list[str]:
    return sorted({column["enum"]["class"] for column in model["columns"] if column["type"] == "enum"})


def _entity_by_name(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {model["entity"]: model for model in plan["models"]}


def _pk(model: dict[str, Any]) -> dict[str, Any]:
    return next(column for column in model["columns"] if column["primaryKey"])


def _snake(entity: str) -> str:
    return to_snake(entity)


def _label(model: dict[str, Any]) -> str:
    """`ContactMessage` → `contact message` (for messages)."""
    return _snake(model["entity"]).replace("_", " ")


# -- database ----------------------------------------------------------------------------------------------------------


def entity_file(model: dict[str, Any]) -> str:
    imports = Imports().add("pydantic", "BaseModel")
    body = []
    for name in _enums(model):
        imports.add("enum", "StrEnum")
        values = next(
            c["enum"]["values"] for c in model["columns"] if c["type"] == "enum" and c["enum"]["class"] == name
        )
        members = "".join(f"    {_member(value)} = {_py(value)}\n" for value in values)
        body.append(f"class {name}(StrEnum):\n{members}")
    fields = []
    for column in model["columns"]:
        annotation = _type(column, imports)
        default = _default(column)
        if column["primaryKey"] or "factory" in default or "autoincrement" in default:
            fields.append(f"    {column['attr']}: {annotation} | None = None")
        elif "value" in default:
            optional = " | None" if column["nullable"] else ""
            fields.append(f"    {column['attr']}: {annotation}{optional} = {_value(column, default['value'])}")
        elif column["nullable"]:
            fields.append(f"    {column['attr']}: {annotation} | None = None")
        else:
            fields.append(f"    {column['attr']}: {annotation}")
    body.append(f"class {model['entityClass']}(BaseModel):\n" + "\n".join(fields) + "\n")
    return imports.render() + "\n\n" + "\n\n".join(body)


def _model_field(column: dict[str, Any], model: dict[str, Any], imports: Imports) -> str:
    annotation = _type(column, imports)
    default = _default(column)
    kwargs: list[str] = []
    nullable = column["nullable"] and not column["primaryKey"]
    if column["primaryKey"]:
        if column["type"] == "uuid":
            kwargs.append("default_factory=uuid.uuid4")
        elif "autoincrement" in default:
            kwargs.append("default=None")
            annotation += " | None"
        kwargs.append("primary_key=True")
    elif "factory" in default:
        if column.get("attr") == "datetime":
            imports.add("datetime as dt")
            imports.add("datetime", "UTC")
            factory = "dt.datetime.now(UTC)"
        else:
            imports.add("datetime", "UTC")
            imports.add("datetime", "datetime")
            factory = "datetime.now(UTC).date()" if column["type"] == "date" else "datetime.now(UTC)"
        kwargs.append(f"default_factory=lambda: {factory}")
    elif "value" in default:
        kwargs.append(f"default={_value(column, default['value'])}")
    elif nullable:
        kwargs.append("default=None")
    foreign = column.get("foreignKey")
    if foreign:
        kwargs.append(f'foreign_key="{foreign["references"]}"')
        kwargs.append(f'ondelete="{foreign["onDelete"]}"')
    if column["type"] == "string" and column.get("maxLength"):
        kwargs.append(f"max_length={column['maxLength']}")
    if column["unique"] and not column["primaryKey"]:
        kwargs.append("unique=True")
    if (column["index"] or foreign) and not column["primaryKey"] and not column["unique"]:
        kwargs.append("index=True")
    sa_type = {
        "text": "Text",
        "decimal": "Numeric(18, 4)",
        "datetime": "DateTime(timezone=True)",
        "json": "JSONB",
    }.get(column["type"])
    if column["type"] == "enum":
        enum = column["enum"]
        imports.add("sqlalchemy", "Enum as SAEnum")
        sa_type = f'SAEnum({enum["class"]}, name="{enum["dbName"]}", values_callable=lambda e: [m.value for m in e])'
    elif sa_type == "JSONB":
        imports.add("sqlalchemy.dialects.postgresql", "JSONB")
    elif sa_type:
        imports.add("sqlalchemy", sa_type.split("(")[0])
    if sa_type:
        kwargs.append(f"sa_type={sa_type}")
    if nullable:
        annotation += " | None"
    if kwargs == ["default=None"]:
        return f"    {column['attr']}: {annotation} = None"
    if not kwargs:
        return f"    {column['attr']}: {annotation}"
    line = f"    {column['attr']}: {annotation} = Field({', '.join(kwargs)})"
    if len(line) <= 120:
        return line
    inner = "".join(f"        {kwarg},\n" for kwarg in kwargs)
    return f"    {column['attr']}: {annotation} = Field(\n{inner}    )"


def model_file(model: dict[str, Any], plan: dict[str, Any]) -> str:
    imports = Imports().add("sqlmodel", "Field", "SQLModel")
    fields = [_model_field(column, model, imports) for column in model["columns"]]
    if _enums(model):
        imports.add("src.modules.shared.domain.entities", *_enums(model))
    relations = []
    referenced = []
    for relation in model.get("relationships", []):
        imports.add("sqlmodel", "Relationship")
        target = re.findall(r'"(\w+)"', relation["annotation"])[0]
        referenced.append(target)
        extra = ', passive_deletes="all"' if relation["annotation"].startswith("list[") else ""
        relations.append(
            f"    {relation['attr']}: {relation['annotation']} = "
            f'Relationship(back_populates="{relation["backPopulates"]}"{extra})'
        )
    checking = ""
    if referenced:
        imports.add("typing", "TYPE_CHECKING")
        by_class = {m["class"]: m for m in plan["models"]}
        lines = "".join(
            f"    from .{by_class[name]['file'].rsplit('/', 1)[1].removesuffix('.py')} import {name}\n"
            for name in sorted(set(referenced))
        )
        checking = f"if TYPE_CHECKING:\n{lines}\n\n"
    body = "\n".join(fields) + ("\n\n" + "\n".join(relations) if relations else "")
    return (
        imports.render()
        + "\n"
        + checking
        + ("" if checking else "\n")
        + f'class {model["class"]}(SQLModel, table=True):\n    __tablename__ = "{model["table"]}"\n\n{body}\n'
    )


def _exports(names: list[str]) -> str:
    quoted = ", ".join(f'"{name}"' for name in names)
    line = f"__all__ = [{quoted}]\n"
    if len(line) <= 121:
        return line
    return "__all__ = [\n" + "".join(f'    "{name}",\n' for name in names) + "]\n"


def database_files(plan: dict[str, Any]) -> dict[str, str]:
    files: dict[str, str] = {}
    entity_exports: list[tuple[str, str]] = []
    model_exports: list[tuple[str, str]] = []
    for model in plan["models"]:
        files[model["entityFile"]] = entity_file(model)
        files[model["file"]] = model_file(model, plan)
        entity_module = model["entityFile"].rsplit("/", 1)[1].removesuffix(".py")
        for name in [model["entityClass"], *_enums(model)]:
            entity_exports.append((entity_module, name))
        model_exports.append((model["file"].rsplit("/", 1)[1].removesuffix(".py"), model["class"]))
    files[f"{ENTITIES_PKG}/__init__.py"] = _package(entity_exports)
    files[f"{MODELS_PKG}/__init__.py"] = _package(model_exports)
    classes = sorted(name for _, name in model_exports)
    registry = Imports().add("src.modules.shared.infrastructure.models", *classes).render()
    files["src/modules/__init__.py"] = (
        '"""Imports every ORM model so Alembic autogenerate discovers it (fastapi-skills pillar 4)."""\n\n'
        + registry
        + "\n"
        + _exports(classes)
    )
    return files


def _package(exports: list[tuple[str, str]]) -> str:
    by_module: dict[str, list[str]] = {}
    for module, name in exports:
        by_module.setdefault(module, []).append(name)
    lines = []
    for module in sorted(by_module):
        names = sorted(by_module[module], key=lambda name: name.lower())
        line = f"from .{module} import {', '.join(names)}"
        lines.append(
            line if len(line) <= 120 else f"from .{module} import (\n" + "".join(f"    {n},\n" for n in names) + ")"
        )
    return "\n".join(lines) + "\n\n" + _exports(sorted(name for _, name in exports))


# -- modules -----------------------------------------------------------------------------------------------------------


class _Module:
    def __init__(self, plan: dict[str, Any], spec: dict[str, Any], module: dict[str, Any]):
        self.plan = plan
        self.module = module
        self.model = _entity_by_name(plan)[module["entity"]]
        self.name = module["name"]
        self.entity = module["entity"]
        self.snake = _snake(self.entity)
        self.entity_class = module["entityClass"]
        self.repo_var = f"{self.snake}_repo"
        self.pk = _pk(self.model)
        self.pkg = f"src.modules.{self.name}"
        self.dir = f"src/modules/{self.name}"
        self.spec_ops = {op["operationId"]: op for op in spec.get("operations", [])}
        self.ops = {op["action"]: op for op in module["operations"] if is_crud(op)}
        self.has_fk = any(column.get("foreignKey") for column in self.model["columns"])
        self.unique = [column for column in self.model["columns"] if column["unique"] and not column["primaryKey"]]

    @property
    def pk_type(self) -> str:
        return _type(self.pk, Imports())

    def _pk_imports(self, imports: Imports) -> str:
        return _type(self.pk, imports)

    def request_columns(self, op: dict[str, Any]) -> list[dict[str, Any]]:
        return _request_columns(self.model, self.spec_ops.get(op["operationId"], {}))

    def search(self) -> list[dict[str, Any]]:
        return (self.ops.get("list") or {}).get("search") or []

    # -- ports & repository ------------------------------------------------------------------------------------

    def port(self) -> str:
        imports = Imports().add("abc", "ABC", "abstractmethod").add(ENTITIES_PKG.replace("/", "."), self.entity_class)
        pk = self._pk_imports(imports) if {"find_by_id", "delete"} & set(self.module["port"]["methods"]) else ""
        entity = self.entity_class
        methods = []
        for method in self.module["port"]["methods"]:
            if method == "create":
                methods.append(f"    def create(self, {self.snake}: {entity}) -> {entity}:\n        pass")
            elif method == "find_by_id":
                methods.append(f"    def find_by_id(self, {self.snake}_id: {pk}) -> {entity} | None:\n        pass")
            elif method == "list":
                imports.add("typing", "Any")
                q = "q: str | None, " if self.search() else ""
                methods.append(
                    "    def list(\n"
                    f"        self, filters: dict[str, Any], {q}sort: tuple[str, bool] | None, "
                    "limit: int, offset: int\n"
                    f"    ) -> tuple[list[{entity}], int]:\n"
                    '        """One page and the total count; `filters` are equality matches on entity attributes."""'
                )
            elif method == "update":
                methods.append(f"    def update(self, {self.snake}: {entity}) -> {entity}:\n        pass")
            elif method == "delete":
                methods.append(f"    def delete(self, {self.snake}_id: {pk}) -> None:\n        pass")
        body = "\n\n".join(f"    @abstractmethod\n{method}" for method in methods)
        return imports.render() + f"\n\nclass {self.module['port']['interface']}(ABC):\n{body}\n"

    def repository(self) -> str:
        port = self.module["port"]
        model = self.module["model"]
        entity = self.entity_class
        imports = (
            Imports()
            .add("typing", "Annotated")
            .add("fastapi", "Depends")
            .add("src.libs.database.session", "SessionDep")
            .add(ENTITIES_PKG.replace("/", "."), entity)
            .add(MODELS_PKG.replace("/", "."), model)
            .add(f"{self.pkg}.ports.output.{port['file'].rsplit('/', 1)[1].removesuffix('.py')}", port["interface"])
        )
        pk = self._pk_imports(imports) if {"find_by_id", "delete"} & set(port["methods"]) else ""
        methods = []
        writes = {"create", "update", "delete"} & set(port["methods"])
        if "create" in port["methods"]:
            methods.append(
                f"    def create(self, {self.snake}: {entity}) -> {entity}:\n"
                f"        model = self.__to_model({self.snake})\n"
                "        self.session.add(model)\n"
                "        self.__flush()\n"
                "        return self.__to_entity(model)"
            )
        if "find_by_id" in port["methods"]:
            methods.append(
                f"    def find_by_id(self, {self.snake}_id: {pk}) -> {entity} | None:\n"
                f"        model = self.session.get({model}, {self.snake}_id)\n"
                "        return self.__to_entity(model) if model else None"
            )
        if "list" in port["methods"]:
            imports.add("typing", "Any").add("sqlmodel", "col", "func", "select")
            search = self.search()
            q_param = "q: str | None, " if search else ""
            q_block = ""
            if search:
                imports.add("sqlmodel", "or_")
                matches = "".join(
                    f"                    col({model}.{item['attr']}).ilike(pattern),\n" for item in search
                )
                q_block = (
                    "        if q:\n"
                    '            pattern = f"%{q}%"\n'
                    "            query = query.where(\n                or_(\n"
                    f"{matches}                )\n            )\n"
                )
            methods.append(
                "    def list(\n"
                f"        self, filters: dict[str, Any], {q_param}sort: tuple[str, bool] | None, "
                "limit: int, offset: int\n"
                f"    ) -> tuple[list[{entity}], int]:\n"
                f"        query = select({model})\n"
                "        for attribute, value in filters.items():\n"
                f"            query = query.where(col(getattr({model}, attribute)) == value)\n"
                + q_block
                + "        total = self.session.exec(select(func.count()).select_from(query.subquery())).one()\n"
                "        if sort:\n"
                f"            column = col(getattr({model}, sort[0]))\n"
                "            query = query.order_by(\n"
                "                column.desc().nulls_last() if sort[1] else column.asc().nulls_last()\n"
                "            )\n"
                f"        query = query.order_by(col({model}.{self.pk['attr']}))\n"
                "        models = self.session.exec(query.offset(offset).limit(limit)).all()\n"
                "        return [self.__to_entity(model) for model in models], total"
            )
        if "update" in port["methods"]:
            methods.append(
                f"    def update(self, {self.snake}: {entity}) -> {entity}:\n"
                f"        model = self.session.get({model}, {self.snake}.{self.pk['attr']})\n"
                f'        for key, value in {self.snake}.model_dump(exclude={{"{self.pk["attr"]}"}}).items():\n'
                "            setattr(model, key, value)\n"
                "        self.__flush()\n"
                "        return self.__to_entity(model)"
            )
        if "delete" in port["methods"]:
            methods.append(
                f"    def delete(self, {self.snake}_id: {pk}) -> None:\n"
                f"        model = self.session.get({model}, {self.snake}_id)\n"
                "        if model is not None:\n"
                "            self.session.delete(model)\n"
                "            self.__flush(deleting=True)"
            )
        if writes:
            imports.add("sqlalchemy.exc", "IntegrityError").add("src.libs.exceptions", "ConflictException")
            label = _label(self.model)
            if self.unique:
                fields = " / ".join(column["apiName"] for column in self.unique)
                conflict = f'"A {label} with this {fields} already exists"'
            else:
                conflict = f'"The {label} conflicts with an existing record"'
            fk_branch = ""
            if self.has_fk or "delete" in port["methods"]:
                imports.add("src.libs.exceptions", "BadRequestException", "ErrorCode")
                missing = (
                    "                raise BadRequestException(\n"
                    '                    "A referenced record does not exist", ErrorCode.REFERENCE_NOT_FOUND\n'
                    "                ) from exc\n"
                )
                fk_branch = (
                    '            if getattr(exc.orig, "pgcode", None) == FOREIGN_KEY_VIOLATION:\n'
                    "                if deleting:\n"
                    "                    raise ConflictException(\n"
                    f'                        "The {label} is still referenced by other records"\n'
                    "                    ) from exc\n" + missing
                )
            methods.append(
                "    def __flush(self, deleting: bool = False) -> None:\n"
                "        try:\n"
                "            self.session.flush()\n"
                "        except IntegrityError as exc:\n"
                + fk_branch
                + f"            raise ConflictException({conflict}) from exc"
            )
        methods.append(
            f"    def __to_entity(self, model: {model}) -> {entity}:\n"
            f"        return {entity}.model_validate(model.model_dump())"
        )
        if "create" in port["methods"]:
            methods.append(
                f"    def __to_model(self, entity: {entity}) -> {model}:\n"
                f"        return {model}(**entity.model_dump(exclude_none=True))"
            )
        constant = (
            f'\nFOREIGN_KEY_VIOLATION = "{FOREIGN_KEY_VIOLATION}"\n'
            if "== FOREIGN_KEY_VIOLATION" in "".join(methods)
            else ""
        )
        return (
            imports.render() + constant + f"\n\nclass {port['implementation']}({port['interface']}):\n"
            "    def __init__(self, session: SessionDep):\n"
            "        self.session = session\n\n"
            + "\n\n".join(methods)
            + f"\n\n\n{port['dep']} = Annotated[{port['interface']}, Depends({port['implementation']})]\n"
        )

    # -- DTOs --------------------------------------------------------------------------------------------------

    def _constraints(self, column: dict[str, Any], required: bool) -> list[str]:
        kwargs = []
        if column["type"] in ("string", "text") and required:
            kwargs.append("min_length=1")
        if column["type"] in ("string", "text") and column.get("maxLength"):
            kwargs.append(f"max_length={column['maxLength']}")
        if column["type"] in ("integer", "float", "decimal"):
            if column.get("min") is not None:
                kwargs.append(f"ge={column['min']}")
            if column.get("max") is not None:
                kwargs.append(f"le={column['max']}")
        return kwargs

    def _dto_imports(self, columns: list[dict[str, Any]], imports: Imports) -> None:
        enums = sorted({c["enum"]["class"] for c in columns if c["type"] == "enum"})
        if enums:
            imports.add(ENTITIES_PKG.replace("/", "."), *enums)

    def create_dto(self) -> str:
        op = self.ops["create"]
        columns = self.request_columns(op)
        imports = Imports().add("pydantic", "BaseModel", "ConfigDict").add("pydantic.alias_generators", "to_camel")
        imports.add(ENTITIES_PKG.replace("/", "."), self.entity_class)
        self._dto_imports(columns, imports)
        fields = []
        for column in columns:
            annotation = _type(column, imports)
            required = _required(column)
            kwargs = self._constraints(column, required)
            default = _default(column).get("value")
            if not required:
                annotation += " | None" if column["nullable"] or default is None else ""
                kwargs.insert(0, f"default={_value(column, default) if default is not None else 'None'}")
            if kwargs and kwargs != ["default=None"]:
                imports.add("pydantic", "Field")
                fields.append(f"    {column['attr']}: {annotation} = Field({', '.join(kwargs)})")
            elif kwargs:
                fields.append(f"    {column['attr']}: {annotation} = None")
            else:
                fields.append(f"    {column['attr']}: {annotation}")
        return (
            imports.render() + f"\n\nclass {op['requestDto']}(BaseModel):\n"
            '    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")\n\n'
            + "\n".join(fields)
            + f"\n\n    def to_entity(self) -> {self.entity_class}:\n"
            f"        return {self.entity_class}(**self.model_dump())\n"
        )

    def update_dto(self) -> str:
        op = self.ops["update"]
        columns = self.request_columns(op)
        imports = Imports().add("pydantic", "BaseModel", "ConfigDict").add("pydantic.alias_generators", "to_camel")
        imports.add(ENTITIES_PKG.replace("/", "."), self.entity_class)
        self._dto_imports(columns, imports)
        fields = []
        for column in columns:
            annotation = _type(column, imports) + " | None"
            kwargs = self._constraints(column, _required(column))
            if kwargs:
                imports.add("pydantic", "Field")
                fields.append(f"    {column['attr']}: {annotation} = Field(default=None, {', '.join(kwargs)})")
            else:
                fields.append(f"    {column['attr']}: {annotation} = None")
        return (
            imports.render() + f"\n\nclass {op['requestDto']}(BaseModel):\n"
            '    """PATCH body: only the fields that are sent change."""\n\n'
            '    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")\n\n'
            + "\n".join(fields)
            + f"\n\n    def to_entity(self, current: {self.entity_class}) -> {self.entity_class}:\n"
            "        return current.model_copy(update=self.model_dump(exclude_unset=True))\n"
        )

    @property
    def response_dto(self) -> str:
        return f"{self.entity}ResponseDto"

    @property
    def response_file(self) -> str:
        return f"{self.snake}_response_dto"

    def response_dto_file(self) -> str:
        imports = Imports().add("pydantic", "BaseModel", "ConfigDict").add("pydantic.alias_generators", "to_camel")
        imports.add(ENTITIES_PKG.replace("/", "."), self.entity_class)
        self._dto_imports(self.model["columns"], imports)
        fields = []
        decimals = []
        for column in self.model["columns"]:
            annotation = _type(column, imports, response=True)
            if column["type"] == "decimal":
                decimals.append(column)
            fields.append(f"    {column['attr']}: {annotation}{' | None' if column['nullable'] else ''}")
        if decimals:
            conversions = ", ".join(
                f'"{c["attr"]}": float(entity.{c["attr"]})'
                if not c["nullable"]
                else f'"{c["attr"]}": None if entity.{c["attr"]} is None else float(entity.{c["attr"]})'
                for c in decimals
            )
            value = f"{{**entity.model_dump(), {conversions}}}"
        else:
            value = "entity.model_dump()"
        line = f"        return cls.model_validate({value})"
        if len(line) > 120:
            line = f"        return cls.model_validate(\n            {value}\n        )"
        return (
            imports.render() + f"\n\nclass {self.response_dto}(BaseModel):\n"
            "    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)\n\n"
            + "\n".join(fields)
            + "\n\n    @classmethod\n"
            f'    def from_entity(cls, entity: {self.entity_class}) -> "{self.response_dto}":\n'
            f"{line}\n"
        )

    def list_dto(self) -> str:
        op = self.ops["list"]
        return (
            "from pydantic import BaseModel, ConfigDict\nfrom pydantic.alias_generators import to_camel\n\n"
            f"from .{self.response_file} import {self.response_dto}\n\n\n"
            f"class {op['responseDto']}(BaseModel):\n"
            "    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)\n\n"
            f"    items: list[{self.response_dto}]\n    total: int\n    limit: int\n    offset: int\n"
        )

    def dto_files(self) -> dict[str, str]:
        files: dict[str, str] = {}
        exports: list[tuple[str, str]] = []
        base = f"{self.dir}/presenter/dtos"
        if {"create", "get", "list", "update"} & set(self.ops):
            files[f"{base}/{self.response_file}.py"] = self.response_dto_file()
            exports.append((self.response_file, self.response_dto))
        for action, builder in (("create", self.create_dto), ("update", self.update_dto), ("list", self.list_dto)):
            op = self.ops.get(action)
            if op is None:
                continue
            name = op["dtoFile"].removesuffix(".py")
            files[f"{base}/{name}.py"] = builder()
            exports.append((name, op["requestDto"] if action != "list" else op["responseDto"]))
        files[f"{base}/__init__.py"] = _package(exports)
        return files

    # -- use cases -----------------------------------------------------------------------------------------------

    def _usecase(self, op: dict[str, Any], imports: Imports, signature: str, body: str, returns: str) -> str:
        repo = self.module["port"]["dep"]
        imports.add("typing", "Annotated").add("fastapi", "Depends").add(f"{self.pkg}.ports.output", repo)
        decorator = ""
        if op["transactional"]:
            imports.add("src.libs.decorators.transactional_decorator", "Transactional")
            decorator = "    @Transactional\n"
        logger = ""
        if "logger." in body:
            imports.add("src.configs", "get_logger")
            logger = "\nlogger = get_logger(__name__)\n"
        return (
            imports.render() + logger + f"\n\nclass {op['usecase']}:\n"
            f"    def __init__(self, {self.repo_var}: {repo}):\n"
            f"        self.{self.repo_var} = {self.repo_var}\n\n"
            f"{decorator}    async def execute(self{signature}) -> {returns}:\n{body}\n\n\n"
            f"{op['usecaseDep']} = Annotated[{op['usecase']}, Depends({op['usecase']})]\n"
        )

    def _raise_not_found(self) -> str:
        return (
            f'            raise NotFoundException("{self.entity} not found", details={{"id": str({self.snake}_id)}})\n'
        )

    def _not_found(self, var: str) -> str:
        return f"        if {var} is None:\n" + self._raise_not_found()

    def usecase_files(self) -> dict[str, str]:
        files = {}
        dtos = f"{self.pkg}.presenter.dtos"
        repo = f"self.{self.repo_var}"
        log_id = f'extra={{"{self.snake}_id": str({self.snake}.{self.pk["attr"]})}}'
        for action, op in self.ops.items():
            imports = Imports()
            pk = self._pk_imports(imports) if action in ("get", "update", "delete") else ""
            if action == "create":
                imports.add(dtos, op["requestDto"], self.response_dto)
                body = (
                    f"        {self.snake} = {repo}.create(dto.to_entity())\n"
                    f'        logger.info("{_label(self.model)} created", {log_id})\n'
                    f"        return {self.response_dto}.from_entity({self.snake})"
                )
                text = self._usecase(op, imports, f", dto: {op['requestDto']}", body, self.response_dto)
            elif action == "get":
                imports.add(dtos, self.response_dto).add("src.libs.exceptions", "NotFoundException")
                body = (
                    f"        {self.snake} = {repo}.find_by_id({self.snake}_id)\n"
                    + self._not_found(self.snake)
                    + f"        return {self.response_dto}.from_entity({self.snake})"
                )
                text = self._usecase(op, imports, f", {self.snake}_id: {pk}", body, self.response_dto)
            elif action == "update":
                imports.add(dtos, op["requestDto"], self.response_dto).add("src.libs.exceptions", "NotFoundException")
                body = (
                    f"        current = {repo}.find_by_id({self.snake}_id)\n"
                    + self._not_found("current")
                    + f"        {self.snake} = {repo}.update(dto.to_entity(current))\n"
                    f'        logger.info("{_label(self.model)} updated", {log_id})\n'
                    f"        return {self.response_dto}.from_entity({self.snake})"
                )
                signature = f", {self.snake}_id: {pk}, dto: {op['requestDto']}"
                text = self._usecase(op, imports, signature, body, self.response_dto)
            elif action == "delete":
                imports.add("src.libs.exceptions", "NotFoundException")
                body = (
                    f"        if {repo}.find_by_id({self.snake}_id) is None:\n"
                    + self._raise_not_found()
                    + f"        {repo}.delete({self.snake}_id)\n"
                    f'        logger.info("{_label(self.model)} deleted", '
                    f'extra={{"{self.snake}_id": str({self.snake}_id)}})'
                )
                text = self._usecase(op, imports, f", {self.snake}_id: {pk}", body, "None")
            else:
                text = self._list_usecase(op, imports)
            files[f"{self.dir}/usecases/{op['usecaseFile']}"] = text
        exports = [(op["usecaseFile"].removesuffix(".py"), op["usecaseDep"]) for op in self.ops.values()]
        files[f"{self.dir}/usecases/__init__.py"] = _package(exports)
        return files

    def _filter_params(self, op: dict[str, Any], imports: Imports) -> list[tuple[str, str, dict[str, Any]]]:
        """(variable, annotation, filter) per list filter."""
        by_attr = {column["attr"]: column for column in self.model["columns"]}
        params = []
        for flt in op.get("filters", []):
            column = by_attr[flt["attr"]]
            variable = flt["attr"] if flt["attr"] not in RESERVED else f"{flt['attr']}_filter"
            params.append((variable, _type(column, imports), flt))
        return params

    def _list_usecase(self, op: dict[str, Any], imports: Imports) -> str:
        imports.add(f"{self.pkg}.presenter.dtos", op["responseDto"], self.response_dto)
        params = self._filter_params(op, imports)
        enums = sorted({annotation for _, annotation, _ in params if annotation[0].isupper() and "." not in annotation})
        if enums:
            imports.add(ENTITIES_PKG.replace("/", "."), *enums)
        signature = "".join(f",\n        {variable}: {annotation} | None" for variable, annotation, _ in params)
        search = self.search()
        if search:
            signature += ",\n        q: str | None"
        signature += ",\n        sort: str | None,\n        limit: int,\n        offset: int,\n    "
        sort_fields = ", ".join(f'"{item["param"]}": "{item["attr"]}"' for item in op.get("sort", []))
        candidates = ", ".join(f'"{flt["attr"]}": {variable}' for variable, _, flt in params)
        q_arg = "q, " if search else ""
        plural = to_snake(self.name)
        body = (
            f"        candidates = {{{candidates}}}\n"
            "        filters = {key: value for key, value in candidates.items() if value is not None}\n"
            + (
                '        order = (SORT_FIELDS[sort.lstrip("-")], sort.startswith("-")) if sort else None\n'
                if op.get("sort")
                else "        order = None\n"
            )
            + f"        {plural}, total = self.{self.repo_var}.list(filters, {q_arg}order, limit, offset)\n"
            f"        return {op['responseDto']}(\n"
            f"            items=[{self.response_dto}.from_entity(item) for item in {plural}],\n"
            "            total=total,\n            limit=limit,\n            offset=offset,\n        )"
        )
        text = self._usecase(op, imports, signature, body, op["responseDto"])
        if op.get("sort"):
            marker = f"\n\nclass {op['usecase']}:"
            text = text.replace(
                marker,
                f"\n# API sort names (camelCase) → entity attributes\nSORT_FIELDS = {{{sort_fields}}}\n{marker}",
                1,
            )
        return text

    # -- router --------------------------------------------------------------------------------------------------

    def router(self) -> str:
        variable = self.module["router"]["variable"]
        imports = Imports().add("fastapi", "APIRouter")
        dtos = f"{self.pkg}.presenter.dtos"
        usecases = f"{self.pkg}.usecases"
        handlers = []
        for op in self.module["operations"]:
            action = op["action"]
            if action not in self.ops:
                continue
            imports.add(usecases, op["usecaseDep"])
            responses = ", ".join(f"{status}: ERROR" for status in sorted({e["status"] for e in op["errors"]}))
            decorator_args = [f'"{op["path"]}"', f'operation_id="{op["operationId"]}"']
            path_params = re.findall(r"\{(\w+)\}", op["path"])
            if action == "delete":
                decorator_args.append("status_code=204")
            else:
                response = op["responseDto"]
                imports.add(dtos, response)
                decorator_args.append(f"response_model={response}")
                if op["status"] != 200:
                    decorator_args.append(f"status_code={op['status']}")
            if responses:
                decorator_args.append(f"responses={{{responses}}}")
            params: list[str] = []
            for name in path_params:
                params.append(f"{name}: {self._pk_imports(imports)}")
            args = [name for name in path_params]
            if action in ("create", "update"):
                imports.add(dtos, op["requestDto"])
                params.append(f"body: {op['requestDto']}")
                args.append("body")
            params.insert(0, f"usecase: {op['usecaseDep']}") if action == "list" else params.append(
                f"usecase: {op['usecaseDep']}"
            )
            returns = "None" if action == "delete" else op["responseDto"]
            if action == "list":
                imports.add("fastapi", "Query")
                list_params, args = self._list_params(op, imports)
                params += list_params
            call = f"usecase.execute({', '.join(args)})"
            statement = f"    await {call}" if action == "delete" else f"    return await {call}"
            decorator = f"@{variable}.{op['method'].lower()}({', '.join(decorator_args)})"
            if len(decorator) > 120:
                decorator = (
                    f"@{variable}.{op['method'].lower()}(\n" + "".join(f"    {a},\n" for a in decorator_args) + ")"
                )
            signature = f"async def {op['handler']}({', '.join(params)}) -> {returns}:"
            if len(signature) > 120 or action == "list":
                signature = (
                    f"async def {op['handler']}(\n" + "".join(f"    {p},\n" for p in params) + f") -> {returns}:"
                )
            handlers.append(f"{decorator}\n{signature}\n{statement}\n")
        return (
            imports.render() + f'\n{variable} = APIRouter(tags=["{self.module["router"]["tag"]}"])\n\n'
            'ERROR = {"description": "Error envelope: {error: {code, message, details}}"}\n\n\n' + "\n\n".join(handlers)
        )

    def _list_params(self, op: dict[str, Any], imports: Imports) -> tuple[list[str], list[str]]:
        params, args = [], []
        filters = self._filter_params(op, imports)
        enums = sorted(
            {annotation for _, annotation, _ in filters if annotation[0].isupper() and "." not in annotation}
        )
        if enums:
            imports.add(ENTITIES_PKG.replace("/", "."), *enums)
        for variable, annotation, flt in filters:
            alias = f', alias="{flt["param"]}"' if flt["param"] != variable else ""
            params.append(f"{variable}: {annotation} | None = Query(default=None{alias})")
            args.append(variable)
        if self.search():
            params.append("q: str | None = Query(default=None)")
            args.append("q")
        if op.get("sort"):
            names = "|".join(item["param"] for item in op["sort"])
            params.append(f'sort: str | None = Query(default=None, pattern=r"^-?({names})$")')
        args.append("sort" if op.get("sort") else "None")
        pagination = op.get("pagination")
        if pagination:
            params.append(
                f"limit: int = Query(default={pagination['defaultLimit']}, ge=1, le={pagination['maxLimit']})"
            )
            params.append("offset: int = Query(default=0, ge=0)")
            args += ["limit", "offset"]
        else:
            args += ["1000", "0"]
        return params, args

    def files(self) -> dict[str, str]:
        port = self.module["port"]
        port_module = port["file"].rsplit("/", 1)[1].removesuffix(".py")
        impl_module = port["implementationFile"].rsplit("/", 1)[1].removesuffix(".py")
        router = self.module["router"]["variable"]
        files = {
            f"{self.dir}/__init__.py": "",
            f"{self.dir}/ports/__init__.py": "",
            f"{self.dir}/infrastructure/__init__.py": "",
            port["file"]: self.port(),
            f"{self.dir}/ports/output/__init__.py": (
                f"from .{port_module} import {port['interface']}  # noqa: I001  (must load before the implementation)\n"
                f"from {self.pkg}.infrastructure.persistence import {port['dep']}\n\n"
                + _exports([port["interface"], port["dep"]])
            ),
            port["implementationFile"]: self.repository(),
            f"{self.dir}/infrastructure/persistence/__init__.py": f"from .{impl_module} import {port['dep']}\n\n"
            + _exports([port["dep"]]),
            self.module["router"]["file"]: self.router(),
            f"{self.dir}/presenter/__init__.py": f"from .router import {router}\n\n" + _exports([router]),
        }
        files |= self.dto_files()
        files |= self.usecase_files()
        return files


def module_files(plan: dict[str, Any], spec: dict[str, Any], module: dict[str, Any]) -> dict[str, str]:
    """Every file of one CRUD module (paths relative to the backend project)."""
    return _Module(plan, spec, module).files()


def routers_file(plan: dict[str, Any]) -> str:
    routers = plan["routers"]["order"]
    by_variable = {module["router"]["variable"]: module for module in plan["modules"]}
    imports = Imports().add("src.modules.health.presenter", "health_router")
    for variable in routers:
        if variable in by_variable:
            imports.add(f"src.modules.{by_variable[variable]['name']}.presenter", variable)
    line = f"all_router = [{', '.join(routers)}]\n"
    if len(line) > 120:
        line = "all_router = [\n" + "".join(f"    {name},\n" for name in routers) + "]\n"
    return imports.render() + "\n" + line


# -- tests -------------------------------------------------------------------------------------------------------------


class _Tests:
    """tests/modules/<module>/test_<entity>_api.py for one CRUD module."""

    def __init__(self, plan: dict[str, Any], spec: dict[str, Any], module: dict[str, Any]):
        self.crud = _Module(plan, spec, module)
        self.plan = plan
        self.module = module
        self.models = _entity_by_name(plan)
        self.by_table = {model["table"]: model for model in plan["models"]}
        self.imports = (
            Imports()
            .add("os")
            .add("uuid")
            .add("itertools", "count")
            .add("typing", "Any")
            .add("sqlalchemy", "create_engine")
            .add("sqlmodel", "Session")
        )
        self.helpers: dict[str, str] = {}

    # -- seeding -------------------------------------------------------------------------------------------------

    def _required(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            column
            for column in model["columns"]
            if not column["primaryKey"] and not column["nullable"] and not _default(column)
        ]

    def _parent(self, column: dict[str, Any]) -> dict[str, Any]:
        return self.by_table[column["foreignKey"]["references"].split(".")[0]]

    def seed(self, model: dict[str, Any]) -> str:
        """The name of `_seed_<entity>(**overrides)`, writing it (and its parents') on first use."""
        name = f"_seed_{_snake(model['entity'])}"
        if name in self.helpers:
            return name
        self.helpers[name] = ""
        self.imports.add(MODELS_PKG.replace("/", "."), model["class"])
        lines = []
        for column in self._required(model):
            if column.get("foreignKey"):
                parent = self._parent(column)
                parent_seed = self.seed(parent)
                lines.append(
                    f'    if "{column["attr"]}" not in values:\n'
                    f'        values["{column["attr"]}"] = {parent_seed}().{_pk(parent)["attr"]}\n'
                )
                continue
            literal = self._literal(column, "n", _label(model).title())
            lines.append(f'    values.setdefault("{column["attr"]}", {literal})\n')
        body = "".join(lines)
        counter = "    n = next(SEQUENCE)\n" if re.search(r"\bn\b", body) else ""
        self.helpers[name] = (
            f"def {name}(**overrides: Any) -> {model['class']}:\n"
            + counter
            + "    values: dict[str, Any] = dict(overrides)\n"
            + body
            + '    engine = create_engine(os.environ["DB_URL"])\n'
            "    with Session(engine) as session:\n"
            f"        model = {model['class']}(**values)\n"
            "        session.add(model)\n"
            "        session.commit()\n"
            "        session.refresh(model)\n"
            "    engine.dispose()\n"
            "    return model\n"
        )
        return name

    def _literal(self, column: dict[str, Any], counter: str, label: str) -> str:
        """A Python expression for a distinct sample value of `column` (using the int variable `counter`)."""
        kind = column["type"]
        if kind in ("string", "text"):
            limit = column.get("maxLength")
            text = f'f"{label} {column["apiName"]} {{{counter}}}"'
            return f"{text}[-{limit}:]" if limit else text
        if kind == "integer":
            low = column.get("min") if column.get("min") is not None else 1
            expression = f"{low} + {counter}"
            return f"min({expression}, {column['max']})" if column.get("max") is not None else expression
        if kind in ("float", "decimal"):
            low = column.get("min") if column.get("min") is not None else 1
            expression = f"{float(low)} + {counter}"
            if column.get("max") is not None:
                expression = f"min({expression}, {float(column['max'])})"
            if kind == "decimal":
                self.imports.add("decimal", "Decimal")
                return f"Decimal(str({expression}))"
            return expression
        if kind == "boolean":
            return f"{counter} % 2 == 1"
        if kind == "date":
            self.imports.add("datetime", "date")
            return f"date(2026, 1, {counter} % 28 + 1)"
        if kind == "datetime":
            self.imports.add("datetime", "UTC", "datetime")
            return f"datetime(2026, 1, {counter} % 28 + 1, 9, 0, tzinfo=UTC)"
        if kind == "enum":
            self.imports.add(ENTITIES_PKG.replace("/", "."), column["enum"]["class"])
            values = column["enum"]["values"]
            return f"list({column['enum']['class']})[{counter} % {len(values)}]"
        if kind == "uuid":
            return "uuid.uuid4()"
        return "{}"

    def _fixed(self, column: dict[str, Any], which: int) -> tuple[str, Any] | None:
        """(Python literal, JSON value) of the `which`-th (0 or 1) of two ordered, distinct values, or None."""
        kind = column["type"]
        if kind in ("string", "text"):
            text = ("Alpha", "Beta")[which]
            return _py(text), text
        if kind == "integer":
            low = column.get("min") if column.get("min") is not None else 1
            value = low + which
            if column.get("max") is not None and value > column["max"]:
                return None
            return repr(value), value
        if kind in ("float", "decimal"):
            low = float(column.get("min") if column.get("min") is not None else 1)
            value = low + which
            if column.get("max") is not None and value > float(column["max"]):
                return None
            if kind == "decimal":
                self.imports.add("decimal", "Decimal")
                return f'Decimal("{value}")', value
            return repr(value), value
        if kind == "boolean":
            return repr(bool(which)), bool(which)
        if kind == "date":
            self.imports.add("datetime", "date")
            return f"date(2026, 1, {which + 1})", f"2026-01-0{which + 1}"
        if kind == "datetime":
            self.imports.add("datetime", "UTC", "datetime")
            return f"datetime(2026, 1, {which + 1}, 9, 0, tzinfo=UTC)", None
        if kind == "enum":
            values = column["enum"]["values"]
            if len(values) < 2:
                return None
            self.imports.add(ENTITIES_PKG.replace("/", "."), column["enum"]["class"])
            return f"{column['enum']['class']}.{_member(values[which])}", values[which]
        return None

    # -- payloads ------------------------------------------------------------------------------------------------

    def payload_helper(self, op: dict[str, Any]) -> str:
        lines = []
        for column in self.crud.request_columns(op):
            if column.get("foreignKey"):
                parent = self._parent(column)
                value = f"str({self.seed(parent)}().{_pk(parent)['attr']})"
            else:
                value = self._json_literal(column)
            lines.append(f'        "{column["apiName"]}": {value},\n')
        body = "".join(lines)
        counter = "    n = next(SEQUENCE)\n" if re.search(r"\bn\b", body) else ""
        return f"def _payload() -> dict[str, Any]:\n{counter}    return {{\n{body}    }}\n"

    def _json_literal(self, column: dict[str, Any]) -> str:
        kind = column["type"]
        label = _label(self.crud.model).title()
        if kind in ("string", "text"):
            limit = column.get("maxLength")
            text = f'f"{label} {column["apiName"]} {{n}}"'
            return f"{text}[-{limit}:]" if limit else text
        if kind == "integer":
            low = column.get("min") if column.get("min") is not None else 1
            return f"min({low} + n, {column['max']})" if column.get("max") is not None else f"{low} + n"
        if kind in ("float", "decimal"):
            low = float(column.get("min") if column.get("min") is not None else 1)
            return f"min({low} + n, {float(column['max'])})" if column.get("max") is not None else f"{low} + n"
        if kind == "boolean":
            return "n % 2 == 1"
        if kind == "date":
            return 'f"2026-01-{n % 28 + 1:02d}"'
        if kind == "datetime":
            return 'f"2026-01-{n % 28 + 1:02d}T09:00:00Z"'
        if kind == "enum":
            values = column["enum"]["values"]
            return f"{_py(values)}[n % {len(values)}]"
        if kind == "uuid":
            return "str(uuid.uuid4())"
        return "{}"

    # -- cases ---------------------------------------------------------------------------------------------------

    def _path(self, op: dict[str, Any], record: str) -> str:
        path = op["path"]
        for name in re.findall(r"\{(\w+)\}", path):
            path = path.replace(f"{{{name}}}", f"{{{record}.{self.crud.pk['attr']}}}")
        return f'f"{path}"' if "{" in path else f'"{path}"'

    def _missing_path(self, op: dict[str, Any]) -> str:
        path = op["path"]
        for name in re.findall(r"\{(\w+)\}", path):
            path = path.replace(f"{{{name}}}", "{MISSING}")
        return f'f"{path}"'

    def case(self, test: dict[str, Any], op: dict[str, Any]) -> str | None:
        name = test["id"]
        case = test["case"]
        action = op["action"]
        seed = self.seed(self.crud.model)
        pk = self.crud.pk["attr"]
        method = op["method"].lower()
        if action == "create":
            if case == "ok":
                checks = [
                    c["apiName"]
                    for c in self.crud.request_columns(op)
                    if c["type"] not in ("datetime", "float", "decimal")
                ]
                compare = "".join(f'    assert body["{api}"] == payload["{api}"]\n' for api in checks)
                return (
                    f"def {name}(client):\n    payload = _payload()\n\n"
                    f'    response = client.post("{op["path"]}", json=payload)\n\n'
                    "    assert response.status_code == 201, response.text\n"
                    "    body = response.json()\n" + compare
                )
            if case == "invalid":
                body = "{}" if any(_required(c) for c in self.crud.request_columns(op)) else '{"unexpectedField": 1}'
                return (
                    f"def {name}(client):\n"
                    f'    assert client.post("{op["path"]}", json={body}).status_code == 422\n'
                    f'    assert client.post("{op["path"]}", json={{**_payload(), "unexpectedField": 1}})'
                    ".status_code == 422\n"
                )
            if case == "conflict":
                return (
                    f"def {name}(client):\n    payload = _payload()\n"
                    f'    assert client.post("{op["path"]}", json=payload).status_code == 201\n\n'
                    f'    response = client.post("{op["path"]}", json=payload)\n\n'
                    "    assert response.status_code == 409\n"
                    '    assert response.json()["error"]["code"] == "CONFLICT"\n'
                )
            if case == "bad_reference":
                fks = [c["apiName"] for c in self.crud.request_columns(op) if c.get("foreignKey")]
                changes = ", ".join(f'"{api}": MISSING' for api in fks)
                return (
                    f"def {name}(client):\n"
                    f'    response = client.post("{op["path"]}", json={{**_payload(), {changes}}})\n\n'
                    "    assert response.status_code == 400\n"
                    '    assert response.json()["error"]["code"] == "REFERENCE_NOT_FOUND"\n'
                )
        if action == "get":
            if case == "ok":
                return (
                    f"def {name}(client):\n    record = {seed}()\n\n"
                    f"    response = client.get({self._path(op, 'record')})\n\n"
                    "    assert response.status_code == 200\n"
                    f'    assert response.json()["{self.crud.pk["apiName"]}"] == str(record.{pk})\n'
                )
            if case == "not_found":
                return (
                    f"def {name}(client):\n    response = client.get({self._missing_path(op)})\n\n"
                    "    assert response.status_code == 404\n"
                    '    assert response.json()["error"]["code"] == "NOT_FOUND"\n'
                )
        if action == "list":
            return self._list_case(name, case, op, seed)
        if action == "update":
            if case == "ok":
                change = self._update_change(op)
                if change is None:
                    return None
                api, value, compare = change
                return (
                    f"def {name}(client):\n    record = {seed}()\n\n"
                    f'    response = client.patch({self._path(op, "record")}, json={{"{api}": {value}}})\n\n'
                    "    assert response.status_code == 200, response.text\n"
                    f'    assert response.json()["{api}"] == {compare}\n'
                    f'    assert response.json()["{self.crud.pk["apiName"]}"] == str(record.{pk})\n'
                )
            if case == "not_found":
                missing = self._missing_path(op)
                return f"def {name}(client):\n    assert client.patch({missing}, json={{}}).status_code == 404\n"
            if case == "invalid":
                return (
                    f"def {name}(client):\n    record = {seed}()\n\n"
                    f'    assert client.patch({self._path(op, "record")}, json={{"unexpectedField": 1}})'
                    ".status_code == 422\n"
                )
        if action == "delete":
            if case == "ok":
                get = self.crud.ops.get("get")
                after = f"    assert client.get({self._path(get, 'record')}).status_code == 404\n" if get else ""
                return (
                    f"def {name}(client):\n    record = {seed}()\n\n"
                    f"    assert client.{method}({self._path(op, 'record')}).status_code == 204\n" + after
                )
            if case == "not_found":
                return f"def {name}(client):\n    assert client.delete({self._missing_path(op)}).status_code == 404\n"
        return None

    def _update_change(self, op: dict[str, Any]) -> tuple[str, str, str] | None:
        """(apiName, new value expression, expected response expression) for the PATCH happy path."""
        columns = [c for c in self.crud.request_columns(op) if not c.get("foreignKey")]
        for column in columns:
            fixed = self._fixed(column, 1)
            if fixed is not None and fixed[1] is not None:
                return column["apiName"], _py(fixed[1]), _py(fixed[1])
        fks = [c for c in self.crud.request_columns(op) if c.get("foreignKey")]
        if fks:
            parent = self._parent(fks[0])
            expression = f"str({self.seed(parent)}().{_pk(parent)['attr']})"
            return fks[0]["apiName"], expression, f'response.json()["{fks[0]["apiName"]}"]'
        return None

    def _list_case(self, name: str, case: str, op: dict[str, Any], seed: str) -> str | None:
        path = f'"{op["path"]}"'
        if case == "ok":
            return (
                f"def {name}(client):\n    first, second = {seed}(), {seed}()\n\n"
                f"    body = client.get({path}).json()\n\n"
                '    assert body["total"] == 2\n'
                f'    assert {{item["{self.crud.pk["apiName"]}"] for item in body["items"]}} == '
                f"{{str(first.{self.crud.pk['attr']}), str(second.{self.crud.pk['attr']})}}\n"
            )
        if case == "pagination":
            return (
                f"def {name}(client):\n    for _ in range(3):\n        {seed}()\n\n"
                f'    page = client.get({path}, params={{"limit": 2, "offset": 2}}).json()\n\n'
                '    assert page["total"] == 3 and page["limit"] == 2 and page["offset"] == 2\n'
                '    assert len(page["items"]) == 1\n'
            )
        if case.startswith("filter_"):
            flt = next(f for f in op.get("filters", []) if f"filter_{to_snake(f['param'])}" == case)
            column = next(c for c in self.crud.model["columns"] if c["attr"] == flt["attr"])
            pk = self.crud.pk
            if column.get("foreignKey"):
                return (
                    f"def {name}(client):\n    first = {seed}()\n    {seed}()\n\n"
                    f'    body = client.get({path}, params={{"{flt["param"]}": str(first.{column["attr"]})}})'
                    ".json()\n\n"
                    f'    assert [item["{pk["apiName"]}"] for item in body["items"]] == [str(first.{pk["attr"]})]\n'
                )
            low, high = self._fixed(column, 0), self._fixed(column, 1)
            if low is None or high is None or low[1] is None:
                return None
            query = _py(low[1]) if column["type"] != "boolean" else _py("true" if low[1] else "false")
            return (
                f"def {name}(client):\n"
                f"    first = {seed}({column['attr']}={low[0]})\n"
                f"    {seed}({column['attr']}={high[0]})\n\n"
                f'    body = client.get({path}, params={{"{flt["param"]}": {query}}}).json()\n\n'
                f'    assert [item["{pk["apiName"]}"] for item in body["items"]] == [str(first.{pk["attr"]})]\n'
            )
        if case == "sort":
            item = op["sort"][0]
            column = next(c for c in self.crud.model["columns"] if c["attr"] == item["attr"])
            low, high = self._fixed(column, 0), self._fixed(column, 1)
            pk = self.crud.pk
            if low is None or high is None:
                return (
                    f"def {name}(client):\n"
                    f'    assert client.get({path}, params={{"sort": "{item["param"]}"}}).status_code == 200\n'
                    f'    assert client.get({path}, params={{"sort": "-{item["param"]}"}}).status_code == 200\n'
                )
            ids = f'[entry["{pk["apiName"]}"] for entry in body["items"]]'
            return (
                f"def {name}(client):\n"
                f"    high = {seed}({column['attr']}={high[0]})\n"
                f"    low = {seed}({column['attr']}={low[0]})\n"
                f"    expected = [str(low.{pk['attr']}), str(high.{pk['attr']})]\n\n"
                f'    body = client.get({path}, params={{"sort": "{item["param"]}"}}).json()\n'
                f"    assert {ids} == expected\n"
                f'    body = client.get({path}, params={{"sort": "-{item["param"]}"}}).json()\n'
                f"    assert {ids} == expected[::-1]\n"
            )
        if case == "invalid_sort":
            return (
                f"def {name}(client):\n"
                f'    assert client.get({path}, params={{"sort": "notAField"}}).status_code == 422\n'
            )
        if case == "search":
            item = next(
                (i for i in op["search"] if self._column(i["attr"])["type"] in ("string", "text")), op["search"][0]
            )
            column = self._column(item["attr"])
            pk = self.crud.pk
            if column["type"] not in ("string", "text"):
                return f'def {name}(client):\n    assert client.get({path}, params={{"q": "x"}}).status_code == 200\n'
            return (
                f"def {name}(client):\n"
                f'    match = {seed}({column["attr"]}="Needle in a haystack")\n'
                f'    {seed}({column["attr"]}="Something else")\n\n'
                f'    body = client.get({path}, params={{"q": "needle"}}).json()\n\n'
                f'    assert [item["{pk["apiName"]}"] for item in body["items"]] == [str(match.{pk["attr"]})]\n'
            )
        return None

    def _column(self, attr: str) -> dict[str, Any]:
        return next(c for c in self.crud.model["columns"] if c["attr"] == attr)

    def render(self) -> str:
        ops = {op["operationId"]: op for op in self.module["operations"]}
        cases = []
        create = self.crud.ops.get("create")
        payload = self.payload_helper(create) if create else ""
        for test in self.module["tests"]:
            op = ops.get(test["operationId"])
            if op is None or not is_crud(op):
                continue
            text = self.case(test, op)
            if text:
                cases.append(text)
        pk = self.crud.pk
        missing = (
            "str(uuid.uuid4())" if pk["type"] == "uuid" else ("999999999" if pk["type"] == "integer" else '"missing"')
        )
        helpers = [text for text in self.helpers.values() if text]
        return (
            '"""Generated by the Fullstack Generation Agent from the plan\'s test cases (Story 17.6)."""\n\n'
            + self.imports.render()
            + f"\nMISSING = {missing}\nSEQUENCE = count(1)\n\n\n"
            + "\n\n".join([*helpers, *([payload] if payload else []), *cases])
        )


def module_tests(plan: dict[str, Any], spec: dict[str, Any], module: dict[str, Any]) -> dict[str, str]:
    """The module's CRUD tests (custom operations' tests are the engine's)."""
    return {module["testFile"]: _Tests(plan, spec, module).render()}
