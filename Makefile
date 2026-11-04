# One command reproduces the whole project: make all
PY ?= python
GOVKIT = $(PY) -m govkit

.PHONY: all install lint validate generate run docs docs-check test app clean

all: lint validate generate run docs test

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

docs:
	$(GOVKIT) docs

# Fails if generated docs are stale (used in CI).
docs-check: docs
	git diff --exit-code -- docs/generated

test:
	$(PY) -m pytest -q

app:
	streamlit run app/app.py

clean:
	rm -rf data reports .pytest_cache
