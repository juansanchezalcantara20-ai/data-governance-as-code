# One command reproduces the whole project: make all
PY ?= python
GOVKIT = $(PY) -m govkit

.PHONY: app-data all install lint validate generate run verify docs docs-check test deploy clean

all: lint validate generate run verify docs app-data test

install:
	$(PY) -m pip install -r requirements.txt && $(PY) -m pip install -e .

lint:
	ruff check .

validate:
	$(GOVKIT) validate

generate:
	$(GOVKIT) generate

run:
	$(GOVKIT) run

verify:
	$(GOVKIT) verify

docs:
	$(GOVKIT) docs

# Data for the demo app, produced only by the engine.
app-data:
	$(GOVKIT) export-app

# Fails if generated docs are stale (used in CI).
docs-check: docs
	git diff --exit-code -- docs/generated deploy/unity_catalog
	$(GOVKIT) export-app --check

test:
	$(PY) -m pytest -q

deploy:
	$(GOVKIT) deploy

clean:
	rm -rf data reports .pytest_cache
