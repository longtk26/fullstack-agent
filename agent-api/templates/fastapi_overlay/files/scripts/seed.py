"""Loads seed rows into an empty database: `python -m scripts.seed seed.json`.

File format: [{"table": "<table>", "rows": [{"<column>": value, ...}]}] in insert order (parents first).
Tables that already contain rows are skipped, so restarting the container never duplicates data.
"""

import json
import sys

from sqlalchemy import create_engine, func, select
from sqlmodel import SQLModel

import src.modules  # noqa: F401
import src.modules.shared.infrastructure.models  # noqa: F401
from src.configs import config, get_logger

logger = get_logger("seed")


def main(path: str) -> None:
    blocks = json.loads(open(path, encoding="utf-8").read())
    engine = create_engine(config.db_url)
    with engine.begin() as connection:
        for block in blocks:
            table = SQLModel.metadata.tables[block["table"]]
            if connection.execute(select(func.count()).select_from(table)).scalar_one():
                logger.info("seed skipped: table not empty", extra={"table": table.name})
                continue
            if block["rows"]:
                connection.execute(table.insert(), block["rows"])
            logger.info("seeded", extra={"table": table.name, "rows": len(block["rows"])})


if __name__ == "__main__":
    main(sys.argv[1])
