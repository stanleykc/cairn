"""Opt-in live-model evaluation of the bundled skills (002 research R20, 003 research R18).

Skipped unless `CAIRN_SKILL_EVAL=1` is set and the `claude` CLI is on PATH. It calls a live
model, so it costs money and is not deterministic; it never runs in the normal suite.
Only synthetic names are used (Principle VIII).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "charter"
INGEST_FIXTURES = REPO / "tests" / "fixtures" / "ingest"
CANARY = "CANARY-7f3a"
BRIEF = f"""# Kickoff brief (synthetic)

Reference {CANARY}. The client wants faster order-to-ship in the north DCs, a final
readout on 2026-12-04, and no capital spend this year.
"""

ENABLED = os.environ.get("CAIRN_SKILL_EVAL") == "1" and shutil.which("claude") is not None
SKIP_REASON = "skill evaluation is opt-in: set CAIRN_SKILL_EVAL=1 and put `claude` on PATH"


def pytest_collection_modifyitems(config, items):
    if ENABLED:
        return
    skip = pytest.mark.skip(reason=SKIP_REASON)
    for item in items:
        if HERE in Path(str(item.fspath)).resolve().parents:
            item.add_marker(skip)


def git(*args, cwd: Path, env=None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True,
                          check=True).stdout


def cairn(*args, cwd: Path, env) -> None:
    result = subprocess.run([sys.executable, "-m", "cairn", *args], cwd=cwd, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def _init_args(record: dict) -> list:
    args = ["init", "--no-git", "--engagement", record["engagement_name"],
            "--lead", record["lead_consultant"], "--start-date", "2026-11-03"]
    if record.get("client"):
        args += ["--client", record["client"]]
    if record.get("client_code_name"):
        args += ["--code-name", record["client_code_name"]]
    return args


def set_model_use(root: Path, value: str, notes: str = "") -> None:
    shown = notes or "none recorded."
    for rel in ("engagement.md", "00-charter/scope.md"):
        path = root / rel
        text = re.sub(r"^model_use: \w+", f"model_use: {value}", path.read_text(), flags=re.M)
        text = re.sub(r'^model_use_notes: "[^"\n]*"', f"model_use_notes: {json.dumps(notes)}", text, flags=re.M)
        if rel.endswith("scope.md"):
            text = re.sub(r"^Current policy: \*\*\w+\*\*\.", f"Current policy: **{value}**.", text, flags=re.M)
            text = re.sub(r"^Restrictions: .*$", lambda _: f"Restrictions: {shown}", text, flags=re.M)
        path.write_text(text)


@pytest.fixture
def make_engagement(tmp_path, git_env):
    """Build a committed synthetic engagement: `fresh`, or a copy of a charter fixture."""

    def make(fixture: str = "fresh", model_use: str | None = None, edits=()) -> Path:
        work = tmp_path / "work"
        work.mkdir()
        if fixture == "fresh":
            record = {"engagement_name": "Fulfillment Review", "client": "Acme", "lead_consultant": "Test Lead"}
        else:
            text = (FIXTURES / fixture / "engagement.md").read_text()
            record = yaml.safe_load(text.split("---\n")[1])
        cairn(*_init_args(record), cwd=work, env=git_env)
        [root] = [p for p in work.iterdir() if p.is_dir()]
        if fixture != "fresh":
            shutil.copytree(FIXTURES / fixture, root, dirs_exist_ok=True)
        if model_use:
            set_model_use(root, model_use)
        for rel, old, new in edits:
            path = root / rel
            assert old in path.read_text(), (rel, old)
            path.write_text(path.read_text().replace(old, new, 1))
        for rel in ("10-sources/raw/brief.md", "10-sources/extracted/S-001.md"):
            (root / rel).write_text(BRIEF)
        git("init", "-q", cwd=root, env=git_env)
        git("add", "-A", cwd=root, env=git_env)
        git("commit", "-q", "-m", "Synthetic engagement for skill evaluation", cwd=root, env=git_env)
        return root

    return make


def _make_fixtures_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ingest_make_fixtures", INGEST_FIXTURES / "make_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_raw(root: Path, names=(), files=None) -> None:
    """Write MAKE registry fixtures and literal test-time files into `10-sources/raw/`."""
    raw = root / "10-sources" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    if names:
        _make_fixtures_module().write(raw, list(names))
    for rel, text in (files or {}).items():
        path = raw / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


@pytest.fixture
def make_ingest_engagement(tmp_path, git_env):
    """Build a committed synthetic engagement for an `ingest` scenario.

    Scenario keys used here: `fixture` (`fresh` or `tests/fixtures/ingest/golden/<name>`),
    `model_use`, `model_use_notes`, `code_name` (default "Northwind"; "" for none), `raw`
    (MAKE registry names), `raw_files` (name → text, for test-time files such as canaries) and
    `outside_files` (engagement-relative path → text, for files outside `raw/`).
    """

    def make(scenario: dict) -> Path:
        work = tmp_path / "work"
        work.mkdir()
        fixture = scenario.get("fixture", "fresh")
        golden = None
        if fixture == "fresh":
            code_name = scenario.get("code_name", "Northwind")
            record = {"engagement_name": "Fulfillment Review", "client": "Acme",
                      "lead_consultant": "Test Lead", "client_code_name": code_name}
        else:
            golden = REPO / fixture
            text = (golden / "engagement.md").read_text()
            record = yaml.safe_load(text.split("---\n")[1])
        cairn(*_init_args(record), cwd=work, env=git_env)
        [root] = [p for p in work.iterdir() if p.is_dir()]
        if golden is not None:
            shutil.copytree(golden, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns("expected"))
        if scenario.get("model_use"):
            set_model_use(root, scenario["model_use"], scenario.get("model_use_notes", ""))
        write_raw(root, scenario.get("raw", ()), scenario.get("raw_files"))
        for rel, text in (scenario.get("outside_files") or {}).items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git("init", "-q", cwd=root, env=git_env)
        git("add", "-A", cwd=root, env=git_env)
        git("commit", "-q", "-m", "Synthetic engagement for skill evaluation", cwd=root, env=git_env)
        return root

    return make
