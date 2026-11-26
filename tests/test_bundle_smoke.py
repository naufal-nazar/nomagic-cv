"""End-to-end smoke test for the standalone skill bundle (dist/nomagic-cv.zip).

Builds the zip, unzips it into a temporary skills folder, creates a fresh virtualenv,
installs only the bundle's own requirements.txt, and runs the checks with that
interpreter in isolated mode (-I) from an empty directory. Nothing from the repository
is on the import path, so a script, rule file, template or dependency missing from the
bundle makes this test fail.

Repository files are used only as *input data*: the fictional Jordan Lee CVs and
application folders from evals/cases/data-analyst. The facts come from the bundle's own
templates/facts.example.yaml.

Needs network access to install the four runtime dependencies (uses uv when available,
pip otherwise). Set NOMAGIC_SKIP_SMOKE=1 to skip it on an offline machine.
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "evals" / "cases" / "data-analyst"
IS_WIN = sys.platform.startswith("win")

pytestmark = pytest.mark.skipif(os.environ.get("NOMAGIC_SKIP_SMOKE") == "1", reason="NOMAGIC_SKIP_SMOKE=1")

# Files the skill needs at runtime, beyond what SKILL.md references (checked separately below).
REQUIRED = [
    "SKILL.md", "requirements.txt", "LICENSE", "LICENSE-CONTENT", "NOTICE.md", "CREDITS.md",
    "rules/rules.yaml", "rules/sources.yaml",
    "templates/facts.example.yaml", "templates/master-cv.md",
    "scripts/cvlib.py", "scripts/fact_check.py", "scripts/consistency_check.py", "scripts/parse_check.py",
    "scripts/posting_guard.py", "scripts/versions.py", "scripts/tracker.py", "scripts/export.py",
]

# Named in SKILL.md, but documented there as full-project only and deliberately left out of the bundle.
FULL_PROJECT_ONLY = {"scripts/setup.py"}

DOCX_HELPER = textwrap.dedent('''
    """Test helper (not shipped): turn clean CV Markdown into a plain single-column DOCX."""
    import sys
    import docx
    src, out = sys.argv[1], sys.argv[2]
    d = docx.Document()
    for line in open(src, encoding="utf-8").read().splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("# "):
            d.add_heading(s[2:], level=0)
        elif s.startswith("## "):
            d.add_heading(s[3:], level=1)
        elif s.startswith("### "):
            d.add_heading(s[4:], level=2)
        elif s.startswith("- "):
            d.add_paragraph(s[2:], style="List Bullet")
        else:
            d.add_paragraph(s.replace("**", ""))
    d.save(out)
''')


def load_setup():
    spec = importlib.util.spec_from_file_location("nm_setup_smoke", ROOT / "scripts" / "setup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_venv(venv_dir: Path, requirements: Path) -> Path:
    py = venv_dir / ("Scripts/python.exe" if IS_WIN else "bin/python")
    uv = shutil.which("uv")
    if uv:
        subprocess.run([uv, "venv", "--quiet", "--python", sys.executable, str(venv_dir)], check=True)
        res = subprocess.run([uv, "pip", "install", "--quiet", "--python", str(py), "-r", str(requirements)],
                             capture_output=True, text=True)
    else:
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        res = subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                              "-r", str(requirements)], capture_output=True, text=True)
    assert res.returncode == 0, f"installing the bundle's requirements.txt failed:\n{res.stdout}\n{res.stderr}"
    return py


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("smoke")
    archive = load_setup().build_zip(tmp / "dist")
    import hashlib
    line = archive.with_name("nomagic-cv.zip.sha256").read_text(encoding="utf-8")
    assert line == f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  nomagic-cv.zip\n"
    skills = tmp / "home" / ".claude" / "skills"
    skills.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        tops = {n.split("/")[0] for n in z.namelist()}
        assert tops == {"nomagic-cv"}, f"zip must have one top-level folder, found {tops}"
        z.extractall(skills)
    skill = skills / "nomagic-cv"
    py = make_venv(tmp / "venv", skill / "requirements.txt")
    run_dir = tmp / "cwd"          # empty working directory: nothing importable from here
    run_dir.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "NOMAGIC_", "CV_", "VIRTUAL_ENV"))}
    env.update({"HOME": str(tmp / "home"), "USERPROFILE": str(tmp / "home"), "CV_TODAY": "2026-11-19",
                "PYTHONUTF8": "1"})
    return {"skill": skill, "py": py, "cwd": run_dir, "env": env, "tmp": tmp}


def run(inst, script: str, *args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {**inst["env"], **(env_extra or {})}
    return subprocess.run([str(inst["py"]), "-I", str(inst["skill"] / "scripts" / script), *args],
                          cwd=inst["cwd"], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_bundle_has_required_files(installed):
    missing = [rel for rel in REQUIRED if not (installed["skill"] / rel).is_file()]
    assert not missing, f"missing from bundle: {missing}"
    assert not (installed["skill"] / "scripts" / "setup.py").exists()


def test_every_path_named_in_the_skill_ships(installed):
    """Any scripts/, references/, templates/ or rules/ path the skill text names must exist in the bundle."""
    skill = installed["skill"]
    pat = re.compile(r"(?<![\w./-])((?:scripts|references|templates|rules)/[\w.-]+\.(?:py|md|yaml|sh))")
    texts = [skill / "SKILL.md", *sorted((skill / "references").glob("*.md"))]
    missing = sorted({f"{t.name}: {m}" for t in texts for m in pat.findall(t.read_text(encoding="utf-8"))
                      if not (skill / m).exists() and m not in FULL_PROJECT_ONLY})
    assert not missing, f"SKILL text names files the bundle lacks: {missing}"


def test_requirements_are_runtime_only_and_match_pyproject(installed):
    req = (installed["skill"] / "requirements.txt").read_text(encoding="utf-8")
    names = {re.split(r"[<>=\[ ]", ln.strip())[0].lower() for ln in req.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")}
    assert "pytest" not in names
    if sys.version_info >= (3, 11):
        import tomllib
        deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
        assert names == {re.split(r"[<>=\[ ]", d)[0].lower() for d in deps}


def test_notice_carries_attribution_and_changes(installed):
    notice = (installed["skill"] / "NOTICE.md").read_text(encoding="utf-8")
    for needle in ("Noufal Nazar", "CC BY 4.0", "https://github.com/naufal-nazar/nomagic-cv",
                   "https://creativecommons.org/licenses/by/4.0/legalcode", "Changes from the repository layout", "MIT"):
        assert needle in notice, needle


def test_every_script_imports_in_the_fresh_venv(installed):
    scripts = installed["skill"] / "scripts"
    mods = sorted(p.stem for p in scripts.glob("*.py"))
    code = f"import sys; sys.path.insert(0, {str(scripts)!r})\n" + "".join(f"import {m}\n" for m in mods)
    res = subprocess.run([str(installed["py"]), "-I", "-c", code], cwd=installed["cwd"], env=installed["env"],
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_fact_check_passes_honest_and_catches_fabricated(installed):
    facts = str(installed["skill"] / "templates" / "facts.example.yaml")
    ok = run(installed, "fact_check.py", str(CASE / "good.md"), "--facts", facts)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = run(installed, "fact_check.py", str(CASE / "fabricated.md"), "--facts", facts)
    assert bad.returncode == 1, bad.stdout + bad.stderr
    for rule in ("R-HONEST-01", "R-HONEST-02", "R-HONEST-03", "R-SIGNAL-05"):
        assert rule in bad.stdout, rule


def test_consistency_check_passes_honest_and_catches_inflated(installed):
    facts = str(installed["skill"] / "templates" / "facts.example.yaml")
    apps = CASE / "applications"
    ok = run(installed, "consistency_check.py", str(apps / "app-consistent"), "--facts", facts)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = run(installed, "consistency_check.py", str(apps / "app-inflated"), "--facts", facts)
    assert bad.returncode == 1, bad.stdout + bad.stderr
    assert "R-KNOCK-02" in bad.stdout and "R-HONEST-05" in bad.stdout


def test_parse_check_reads_exported_docx(installed):
    tmp = installed["tmp"]
    clean = tmp / "clean.md"
    res = run(installed, "export.py", "clean", str(CASE / "good.md"), "-o", str(clean))
    assert res.returncode == 0, res.stderr
    helper = tmp / "helpers" / "md_to_docx.py"
    helper.parent.mkdir(exist_ok=True)
    helper.write_text(DOCX_HELPER, encoding="utf-8")
    docx_path = tmp / "Jordan_Lee_Data_Analyst.docx"
    subprocess.run([str(installed["py"]), "-I", str(helper), str(clean), str(docx_path)], check=True,
                   cwd=installed["cwd"], env=installed["env"])
    res = run(installed, "parse_check.py", str(docx_path), "--source", str(CASE / "good.md"))
    assert res.returncode == 0, res.stdout + res.stderr
    assert res.stdout.startswith("OK") or "\nOK" in res.stdout


def test_posting_guard_runs(installed):
    res = run(installed, "posting_guard.py", str(CASE / "posting_malicious.md"))
    assert res.returncode != 0 and "instruction" in (res.stdout + res.stderr).lower()


def test_versions_init_uses_bundled_template_and_default_workspace(installed):
    res = run(installed, "versions.py", "init", "data-analyst")
    assert res.returncode == 0, res.stdout + res.stderr
    draft = installed["tmp"] / "home" / "nomagic-cv-workspace" / "cvs" / "data-analyst" / "draft.md"
    assert draft.is_file(), "standalone installs must default to ~/nomagic-cv-workspace"
    assert "FIRSTNAME LASTNAME" in draft.read_text(encoding="utf-8"), "draft was not filled from templates/master-cv.md"


def test_skill_text_scopes_every_hook_claim(installed):
    """A standalone install has no hooks, so every mention of one must say it is full-project only."""
    skill = installed["skill"]
    offenders = []
    for t in [skill / "SKILL.md", *sorted((skill / "references").glob("*.md"))]:
        in_scope_section = False
        for no, line in enumerate(t.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("## "):
                in_scope_section = "standalone" in line.lower()
            if in_scope_section:
                continue
            if re.search(r"\bhooks?\b", line, re.I) and not re.search(r"full project|standalone", line, re.I):
                offenders.append(f"{t.name}:{no}: {line.strip()[:100]}")
    assert not offenders, "hook claims without full-project/standalone scope:\n" + "\n".join(offenders)


def test_schedule_explains_it_needs_the_full_project(installed):
    res = run(installed, "schedule.py", "install", "--agent", "claude")
    assert res.returncode == 2 and "full project clone" in res.stderr
