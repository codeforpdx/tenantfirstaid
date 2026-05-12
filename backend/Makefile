PYTHON := uv
PIP := $(PYTHON) pip
.PHONY: all install test clean check generate-types generate-metadata

all: check

uv.lock: pyproject.toml
	$(PYTHON) sync

install:
	$(PIP) install .

fmt: uv.lock
	$(PYTHON) run ruff check --select I --fix
	$(PYTHON) run ruff format

lint: uv.lock
	$(PYTHON) run ruff check $(LINT_OPTIONS)

typecheck: uv.lock
	$(PYTHON) run ty check $(TYPECHECK_OPTIONS)

MYPY_CMD := $(PYTHON) run mypy $(TYPECHECK_OPTIONS)
MYPY_ARGS :=  --python-executable .venv/bin/python3 --pretty --check-untyped-defs

typecheck-mypy-evaluate: uv.lock
	$(MYPY_CMD) -p evaluate $(MYPY_ARGS)

typecheck-mypy-scripts: uv.lock
	$(MYPY_CMD) -p scripts $(MYPY_ARGS)

typecheck-mypy-tenantfirstaid: uv.lock
	$(MYPY_CMD) -p tenantfirstaid $(MYPY_ARGS)

typecheck-mypy: typecheck-mypy-tenantfirstaid typecheck-mypy-evaluate typecheck-mypy-scripts

typecheck-pyrefly: uv.lock
	$(PYTHON) run pyrefly check $(TYPECHECK_OPTIONS) --python-interpreter-path .venv/bin/python3

test: uv.lock
	uv run pytest -v -s $(TEST_OPTIONS)

generate-types: uv.lock
	cd ../frontend && npm run generate-types

# Pass the GCS bucket name via: make generate-metadata GCS_BUCKET_NAME=my-bucket
# Selective runs (e.g. LOC_OPTIONS="--portland") overwrite metadata.jsonl with
# only those entries. Run without LOC_OPTIONS to regenerate the full corpus.
generate-metadata: uv.lock
ifeq ($(strip $(GCS_BUCKET_NAME)),)
	$(error GCS_BUCKET_NAME is required: make generate-metadata GCS_BUCKET_NAME=my-bucket)
endif
	$(PYTHON) run generate-metadata --bucket $(GCS_BUCKET_NAME) $(LOC_OPTIONS)

clean:
	find . -type d -name '__pycache__' -exec rm -r {} +
	rm -rf dist build *.egg-info

check: clean install fmt lint typecheck test
