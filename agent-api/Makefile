run:
	fastapi dev src/main.py
worker:
	python -m src.worker
newmg:
	alembic revision --autogenerate -m "$(name)"
mghead:
	alembic upgrade head
mgdown:
	alembic downgrade -1
schema:
	python -m scripts.export_spec_schema
test:
	pytest
lint:
	ruff check . && ruff format --check .

.PHONY: run worker newmg mghead mgdown schema test lint
