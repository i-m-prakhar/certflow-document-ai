.PHONY: setup generate evaluate ingest serve test lint benchmark docker
setup:
	uv sync --extra dev
generate:
	uv run certflow generate-data
evaluate:
	uv run certflow evaluate
ingest:
	uv run certflow ingest-demo
serve:
	uv run uvicorn certflow.api:app --host 127.0.0.1 --port 8001
test:
	uv run --extra dev pytest -q
lint:
	uv run --extra dev ruff check src tests
benchmark:
	uv run python scripts/benchmark_api.py
docker:
	docker compose up --build
