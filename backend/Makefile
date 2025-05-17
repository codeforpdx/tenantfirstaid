PYTHON := uv
PIP := $(PYTHON) pip

.PHONY: all install test clean check

all: check

install:
	$(PIP) install .

test:
	uv run pytest -v -s

clean:
	find . -type d -name '__pycache__' -exec rm -r {} +
	rm -rf dist build *.egg-info

check: clean install test
