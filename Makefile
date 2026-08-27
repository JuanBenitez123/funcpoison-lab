.PHONY: test typecheck experiment exploit build up patched plots clean

test:
	cd orchestrator && npm test
	cd analyzer && npm test
	python -m pytest tests -q

typecheck:
	cd orchestrator && npm run typecheck
	cd analyzer && npm run typecheck

experiment:
	python experiments/run_all.py

plots: experiment

exploit:
	python exploit/run.py

build:
	docker compose build

up:
	docker compose up --build

patched:
	docker compose -f docker-compose.yml -f docker-compose.patched.yml up --build

clean:
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
	find . -type d -name .pytest_cache -not -path './.venv/*' -exec rm -rf {} +
	docker compose down --remove-orphans || true
