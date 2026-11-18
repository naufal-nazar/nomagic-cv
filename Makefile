.PHONY: setup workspace check test evals lint

setup: ## install deps, git privacy hook, workspace folders, skill links
	python3 -m pip install -r requirements.txt
	git config core.hooksPath scripts/git-hooks
	chmod +x scripts/git-hooks/pre-commit scripts/cross_review.sh hooks/dispatch.py
	$(MAKE) workspace
	@echo "Done. Open Claude Code or Codex here and run /cv-start (or say 'run cv-start')."

workspace:
	mkdir -p workspace/cvs/masters workspace/applications

lint:
	python3 scripts/rules_lint.py

test:
	python3 -m pytest -q

evals:
	python3 evals/run_evals.py

check: lint test evals
