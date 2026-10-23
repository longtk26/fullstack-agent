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
test:
	pytest
lint:
	ruff check . && ruff format --check .

.PHONY: run worker newmg mghead mgdown test lint
