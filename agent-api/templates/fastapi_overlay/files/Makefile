run:
	fastapi dev src/main.py
newmg:
	alembic revision --autogenerate -m "$(name)"
mghead:
	alembic upgrade head
mgdown:
	alembic downgrade -1
test:
	pytest -q
lint:
	ruff check . && ruff format --check .

.PHONY: run newmg mghead mgdown test lint
