.PHONY: install install-dev test lint check postgres-hdd-setup run-mock clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

check: lint test

postgres-hdd-setup:
	bash scripts/setup_postgres_hdd.sh

run-mock:
	LEAD_LIMIT=1 $(PYTHON) -m lead_dispatcher.main

clean:
	rm -rf .pytest_cache .ruff_cache build dist htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
