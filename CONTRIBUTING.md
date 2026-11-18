# Contributing

Thanks for helping. This project has one rule above all: **evidence over folklore**.

## Adding or changing a rule
1. Add the source to `rules/sources.yaml`: title, authors, venue, URL, grade, setting (field/lab for grade A), sample, exact finding, region, `status: verified`, `checked` date.
2. Add or edit the rule in `rules/rules.yaml` with an id like `R-SCAN-05`.
3. Choose strength honestly:
   - `default` needs at least one verified grade A or B source.
   - `test` for grade C or practice: a starting point, never a hard rule.
   - `guardrail` for honesty rules, which need no study.
4. Run `make check`. `scripts/rules_lint.py` fails the build if the evidence gate is not met.

Grades: A = peer-reviewed experiment or field study; B = large controlled experiment or dataset, not peer-reviewed; C = survey or vendor analysis.

## Evidence from other markets
Most studies are from North America and Europe. Studies from other regions are especially welcome; tag them with `region`.

## Code
- Dependencies are managed with [uv](https://docs.astral.sh/uv/): `uv sync` for the environment, `uv add <pkg>` to add one (keep `requirements.txt` in step for the pip fallback), `uv run --group dev pytest -q` for tests.
- Python 3.10+, standard library plus PyYAML. Keep scripts dependency-light and deterministic.
- Add tests in `tests/` and, for new checks, an eval case in `evals/cases/` with an `expected.yaml`.
- Never weaken a check to make a CV pass.

## Model benchmark results
Save model outputs as `evals/out/<model>/<case>.md` and run `python evals/model_bench.py`. Include the model version, date and the exact prompt in your PR.

## Privacy
Never commit real personal data. Eval cases must be fictional. `workspace/` is gitignored and blocked by the pre-commit hook.

## Re-checking sources
Sources are re-checked yearly. If a link breaks or a figure changes, update `checked`, or set `status: unverified` until fixed.
