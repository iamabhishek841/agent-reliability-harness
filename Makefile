.PHONY: up down seed ingest test eval chaos-reset verify

up:
	docker compose up --build

down:
	docker compose down

seed:
	docker compose --profile tools run --rm legacy-seed

ingest:
	docker compose run --rm knowledge-ingest

test:
	docker compose run --rm backend pytest -q eval

eval:
	docker compose run --rm backend python eval/run_eval.py

chaos-reset:
	docker compose --profile tools run --rm chaos python chaos/reset.py

verify:
	python scripts/verify_project.py

