.PHONY: setup zip workspace check test evals lint

PY := $(shell command -v uv >/dev/null 2>&1 && echo "uv run" || echo python3)

setup: ## cross-platform setup (uses uv when installed, pip otherwise)
	$(PY) scripts/setup.py

zip: ## build dist/nomagic-cv.zip for the Claude app
	$(PY) scripts/setup.py --zip --skip-tests

workspace:
	mkdir -p workspace/sources workspace/cvs workspace/applications

lint:
	$(PY) scripts/rules_lint.py

test:
	$(PY) -m pytest -q

evals:
	$(PY) evals/run_evals.py

check: lint test evals
