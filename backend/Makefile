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

MYPY_CMD := $(PYTHON) run mypy $(TYPECHECK_OPTIONS)
MYPY_ARGS :=  --python-executable .venv/bin/python3 --pretty --check-untyped-defs

typecheck-mypy-scripts: uv.lock
	$(MYPY_CMD) -p scripts $(MYPY_ARGS)

typecheck-mypy-tenantfirstaid: uv.lock
	$(MYPY_CMD) -p tenantfirstaid $(MYPY_ARGS)

typecheck-mypy: typecheck-mypy-tenantfirstaid typecheck-mypy-scripts

typecheck-pyrefly: uv.lock
	$(PYTHON) run pyrefly check $(TYPECHECK_OPTIONS) --python-interpreter .venv/bin/python3

test: uv.lock
	uv run pytest -v -s $(TEST_OPTIONS)

clean:
	find . -type d -name '__pycache__' -exec rm -r {} +
	rm -rf dist build *.egg-info

check: clean install fmt lint typecheck test
