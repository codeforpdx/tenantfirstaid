PYTHON := uv
PIP := $(PYTHON) pip
.PHONY: all install test clean check generate-types generate-frontend-assets generate-metadata enforce-ascii upload-to-gcs create-datastore-gcs create-app-gcs

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
	uv run pytest -v $(TEST_OPTIONS)

generate-types: uv.lock
	cd ../frontend && npm run generate-types

generate-frontend-assets: uv.lock
	cd ../frontend && npm run generate-frontend-assets

# Pass the GCS bucket name via: make generate-metadata GCS_BUCKET_NAME=my-bucket
# Selective runs (e.g. LOC_OPTIONS="--portland") overwrite metadata.jsonl with
# only those entries. Run without LOC_OPTIONS to regenerate the full corpus.
generate-metadata: uv.lock
ifeq ($(strip $(GCS_BUCKET_NAME)),)
	$(error GCS_BUCKET_NAME is required: make generate-metadata GCS_BUCKET_NAME=my-bucket)
endif
	$(PYTHON) run python -m scripts.generate_metadata_jsonl --bucket $(GCS_BUCKET_NAME) $(LOC_OPTIONS)

# Validate and rewrite the documents tree to pure ASCII. Pass ASCII_OPTIONS="--check"
# to validate without rewriting (suitable for CI).
enforce-ascii: uv.lock
	$(PYTHON) run python -m scripts.enforce_ascii $(ASCII_OPTIONS)

# Create a new GCS bucket (fails if it already exists) and upload every file
# referenced by metadata.jsonl plus metadata.jsonl itself. The default location
# lives in scripts/upload_to_gcs.py; LOCATION overrides it when set.
#   make upload-to-gcs GCS_BUCKET_NAME=my-bucket
#   make upload-to-gcs GCS_BUCKET_NAME=my-bucket LOCATION=us-central1
#   make upload-to-gcs GCS_BUCKET_NAME=my-bucket UPLOAD_OPTIONS="--dry-run"
upload-to-gcs: uv.lock
ifeq ($(strip $(GCS_BUCKET_NAME)),)
	$(error GCS_BUCKET_NAME is required: make upload-to-gcs GCS_BUCKET_NAME=my-bucket)
endif
	$(PYTHON) run python -m scripts.upload_to_gcs --bucket $(GCS_BUCKET_NAME) $(if $(LOCATION),--location $(LOCATION)) $(UPLOAD_OPTIONS)

# Create a Vertex AI Search datastore and import documents from a GCS bucket.
# Requires GCS_BUCKET_NAME (must match the bucket used with upload-to-gcs) and DATASTORE_ID.
# DATASTORE_ID is the resource ID for the new datastore; reuse the same value as
# DATASTORE_ID for create-app-gcs to link the Search app to it.
#   make create-datastore-gcs GCS_BUCKET_NAME=my-bucket DATASTORE_ID=my-ds
#   make create-datastore-gcs GCS_BUCKET_NAME=my-bucket DATASTORE_ID=my-ds LOCATION=us
#   make create-datastore-gcs GCS_BUCKET_NAME=my-bucket DATASTORE_ID=my-ds DATASTORE_OPTIONS="--no-wait"
create-datastore-gcs: uv.lock
ifeq ($(strip $(GCS_BUCKET_NAME)),)
	$(error GCS_BUCKET_NAME is required: make create-datastore-gcs GCS_BUCKET_NAME=my-bucket DATASTORE_ID=my-ds)
endif
ifeq ($(strip $(DATASTORE_ID)),)
	$(error DATASTORE_ID is required: make create-datastore-gcs GCS_BUCKET_NAME=my-bucket DATASTORE_ID=my-ds)
endif
	$(PYTHON) run python -m scripts.create_datastore_gcs --bucket $(GCS_BUCKET_NAME) --datastore-id $(DATASTORE_ID) $(if $(LOCATION),--location $(LOCATION)) $(DATASTORE_OPTIONS)

# Create a Vertex AI Search app and link it to an existing datastore.
# Requires DATASTORE_ID (from create-datastore-gcs output) and APP_ID.
#   make create-app-gcs DATASTORE_ID=my-ds APP_ID=my-app
#   make create-app-gcs DATASTORE_ID=my-ds APP_ID=my-app LOCATION=us
#   make create-app-gcs DATASTORE_ID=my-ds APP_ID=my-app APP_OPTIONS="--dry-run"
create-app-gcs: uv.lock
ifeq ($(strip $(DATASTORE_ID)),)
	$(error DATASTORE_ID is required: make create-app-gcs DATASTORE_ID=my-ds APP_ID=my-app)
endif
ifeq ($(strip $(APP_ID)),)
	$(error APP_ID is required: make create-app-gcs DATASTORE_ID=my-ds APP_ID=my-app)
endif
	$(PYTHON) run python -m scripts.create_app_gcs --datastore-id $(DATASTORE_ID) --app-id $(APP_ID) $(if $(LOCATION),--location $(LOCATION)) $(APP_OPTIONS)

clean:
	find . -type d -name '__pycache__' -exec rm -r {} +
	rm -rf dist build *.egg-info

check: clean install fmt lint typecheck test
