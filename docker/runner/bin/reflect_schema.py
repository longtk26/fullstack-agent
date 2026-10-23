"""Prints the live database schema (after migrations) as JSON for the schema-vs-plan check."""

import json
import os

from sqlalchemy import create_engine, inspect, text


def _type_name(column_type) -> str:
    if getattr(column_type, "enums", None) is not None and getattr(column_type, "name", None):
        return f"ENUM({column_type.name})"
    if getattr(column_type, "timezone", False):
        return "TIMESTAMP WITH TIME ZONE"
    return str(column_type)


engine = create_engine(os.environ["DB_URL"])
inspector = inspect(engine)
tables = {}
for name in inspector.get_table_names():
    if name == "alembic_version":
        continue
    tables[name] = {
        "columns": [
            {"name": c["name"], "type": _type_name(c["type"]), "nullable": c["nullable"]}
            for c in inspector.get_columns(name)
        ],
        "primaryKey": inspector.get_pk_constraint(name).get("constrained_columns", []),
        "foreignKeys": [
            {
                "columns": fk["constrained_columns"],
                "referredTable": fk["referred_table"],
                "referredColumns": fk["referred_columns"],
                "onDelete": (fk.get("options") or {}).get("ondelete"),
            }
            for fk in inspector.get_foreign_keys(name)
        ],
        "uniques": [u["column_names"] for u in inspector.get_unique_constraints(name)],
        "indexes": [{"columns": i["column_names"], "unique": bool(i["unique"])} for i in inspector.get_indexes(name)],
    }
with engine.connect() as connection:
    rows = connection.execute(
        text(
            "SELECT t.typname, e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid "
            "ORDER BY t.typname, e.enumsortorder"
        )
    )
    enums: dict[str, list[str]] = {}
    for type_name, label in rows:
        enums.setdefault(type_name, []).append(label)
print("BGA_SCHEMA_BEGIN")
print(json.dumps({"tables": tables, "enums": enums}))
