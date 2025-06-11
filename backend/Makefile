PYTHON := uv
PIP := $(PYTHON) pip

.PHONY: all install test clean check

all: check

uv.lock: pyproject.toml
	$(PYTHON) sync

install:
	$(PIP) install .

fmt: uv.lock
	$(PYTHON) run ruff format

lint: uv.lock
	$(PYTHON) run ruff check $(LINT_OPTIONS)

typecheck: uv.lock
	$(PYTHON) run ty check $(TYPECHECK_OPTIONS)

test: uv.lock
	uv run pytest -v -s $(TEST_OPTIONS)

clean:
	find . -type d -name '__pycache__' -exec rm -r {} +
	rm -rf dist build *.egg-info

check: clean install fmt lint typecheck test
