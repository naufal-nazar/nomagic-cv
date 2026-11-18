.PHONY: setup zip workspace check test evals lint

setup: ## cross-platform setup (same as python3 scripts/setup.py)
	python3 scripts/setup.py

zip: ## build dist/nomagic-cv.zip for the Claude app
	python3 scripts/setup.py --zip --skip-tests

workspace:
	mkdir -p workspace/cvs/masters workspace/applications

lint:
	python3 scripts/rules_lint.py

test:
	python3 -m pytest -q

evals:
	python3 evals/run_evals.py

check: lint test evals
