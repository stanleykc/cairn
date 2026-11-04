"""Opt-in live-model evaluation of the `charter` skill (research R20).

Skipped unless `CAIRN_SKILL_EVAL=1` is set and the `claude` CLI is on PATH. It calls a live
model, so it costs money and is not deterministic; it never runs in the normal suite.
Only synthetic names are used (Principle VIII).
"""

from __future__ import annotations

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


def set_model_use(root: Path, value: str) -> None:
    for rel in ("engagement.md", "00-charter/scope.md"):
        path = root / rel
        text = re.sub(r"^model_use: \w+", f"model_use: {value}", path.read_text(), flags=re.M)
        text = re.sub(r'^model_use_notes: "[^"\n]*"', 'model_use_notes: ""', text, flags=re.M)
        if rel.endswith("scope.md"):
            text = re.sub(r"^Current policy: \*\*\w+\*\*\.", f"Current policy: **{value}**.", text, flags=re.M)
            text = re.sub(r"^Restrictions: .*$", "Restrictions: none recorded.", text, flags=re.M)
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
