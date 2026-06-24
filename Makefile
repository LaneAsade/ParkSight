.PHONY: install run-pipeline run-backend run-frontend test test-pipeline lint clean

install:
	pip install -e .[dev]

run-pipeline:
	python scripts/run_pipeline.py

run-backend:
	python scripts/run_backend.py

run-frontend:
	bash scripts/run_frontend.sh

test:
	cd backend && pytest tests/ -v --tb=short

test-pipeline:
	pytest tests/pipeline/ -v --tb=short

lint:
	ruff check parksight backend
	ruff format --check parksight backend

clean:
	rm -rf __pycache__ parksight/__pycache__ backend/app/__pycache__
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
