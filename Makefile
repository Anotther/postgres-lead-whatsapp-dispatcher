.PHONY: install install-dev test lint check clean

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

clean:
	rm -rf .pytest_cache .ruff_cache build dist htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
