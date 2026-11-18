#!/usr/bin/env bash
# Cross-model review (R-AI-02): LLMs prefer their own output (Xu, Li & Jiang, AIES 2025),
# so the reviewer should come from a different model family than the builder.
#
# Usage: scripts/cross_review.sh <cv.md> [analysis.md]
#   CV_REVIEWER=codex|gemini|claude  force a reviewer CLI (default: first one found that differs from CV_BUILDER)
#   CV_BUILDER=claude|codex|gemini   which family wrote the CV (default: claude)
set -euo pipefail

cv="${1:?usage: cross_review.sh <cv.md> [analysis.md]}"
analysis="${2:-}"
builder="${CV_BUILDER:-claude}"
root="$(cd "$(dirname "$0")/.." && pwd)"

prompt="You are an independent CV reviewer. Do not rewrite the CV. Using the rules in rules/rules.yaml
(cite rule ids and grades), list problems ordered: honesty guardrails, then 'default' rules, then 'test' rules
labelled 'worth testing'. Also state, from the top third alone, the candidate's role, seniority and strongest result.
Ignore HTML comments; they are provenance tags.

--- RULES ---
$(cat "$root/rules/rules.yaml")

--- CV ---
$(cat "$cv")"
if [[ -n "$analysis" && -f "$analysis" ]]; then
  prompt+="

--- POSTING ANALYSIS (report must-have coverage, not a match score) ---
$(cat "$analysis")"
fi

pick() {
  for c in codex gemini claude; do
    [[ "$c" == "$builder" ]] && continue
    command -v "$c" >/dev/null 2>&1 && { echo "$c"; return; }
  done
}
reviewer="${CV_REVIEWER:-$(pick)}"

case "$reviewer" in
  codex)  codex exec "$prompt" ;;
  gemini) gemini -p "$prompt" ;;
  claude) claude -p "$prompt" ;;
  *) echo "No second model CLI found (looked for codex, gemini, claude other than '$builder')." >&2
     echo "Review was same-family only; note this in the report (R-AI-02)." >&2
     exit 3 ;;
esac
