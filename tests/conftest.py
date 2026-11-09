"""Shared helpers. Only synthetic names are used (Principle VIII)."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest

ACME = "Acme"
GLOBEX = "Globex"
GLOBEX_CORP = "Globex Corporation"
FALCON = "Falcon"
FULFILLMENT = "Fulfillment Review"
PRICING = "Pricing Study"
LEAD = "Test Lead"

ACME_ID = "acme-fulfillment-review"
INIT_ACME = ("init", "--engagement", FULFILLMENT, "--client", ACME, "--lead", LEAD)

PACKAGE_ASSETS = Path(str(files("cairn") / "assets"))


def make_git_env(tmp_path: Path) -> dict[str, str]:
    config = tmp_path / "gitconfig"
    config.write_text(
        "[user]\n\tname = Test Lead\n\temail = test-lead@example.invalid\n"
        "[init]\n\tdefaultBranch = main\n"
    )
    env = dict(os.environ)
    env.update(GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM="1")
    for key in ("CAIRN_ASSETS_DIR", "CAIRN_FRAMEWORK_VERSION"):
        env.pop(key, None)
    return env


@pytest.fixture
def git_env(tmp_path) -> dict[str, str]:
    """Environment with a synthetic git identity and no system git config."""
    return make_git_env(tmp_path)


def run_cairn(*args, cwd, env=None, input=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "cairn", *map(str, args)],
        cwd=cwd,
        env=env,
        input=input,
        stdin=subprocess.DEVNULL if input is None else None,
        capture_output=True,
        text=True,
    )


def tree_hash(path: Path, exclude=()) -> dict[str, str]:
    """Map each file's relative POSIX path to its SHA-256, skipping excluded prefixes."""
    path = Path(path)
    result = {}
    for file in sorted(path.rglob("*")):
        if not file.is_file():
            continue
        rel = file.relative_to(path).as_posix()
        if any(rel == e or rel.startswith(e.rstrip("/") + "/") for e in exclude):
            continue
        result[rel] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def fixture_assets(
    tmp_path: Path, version="0.1.0", skills=None, name="assets", bundled_skills=True
) -> dict[str, str]:
    """Copy the package assets to `tmp_path/name`, add `skills`, and return env additions.

    `skills` maps a skill name to its SKILL.md text, or to a dict of relative path → text.
    With `bundled_skills=False`, the package's own skills (such as `charter`) are removed
    first, so the copy holds exactly the skills given in `skills`.
    """
    root = tmp_path / name
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(PACKAGE_ASSETS, root)
    if not bundled_skills:
        for folder in (root / "skills").iterdir():
            if folder.is_dir():
                shutil.rmtree(folder)
    for skill, content in (skills or {}).items():
        entries = content if isinstance(content, dict) else {"SKILL.md": content}
        for rel, text in entries.items():
            dest = root / "skills" / skill / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
    return {"CAIRN_ASSETS_DIR": str(root), "CAIRN_FRAMEWORK_VERSION": version}


QUESTION_ENTRY = """## {id}: {title}

```yaml
id: "{id}"
type: question
title: {title_json}
status: {status}
origin: consultant-note
confidence: medium
confidence_reason: "Raised by the sponsor at kickoff"
inference_confirmed: false
audience: internal
supports: []
contradicts: []
derived_from: []
supersedes: []
clarifies: []
change_reason: ""
change_trigger: ""
created: "2026-11-03"
priority: medium
raised_by: "Test Lead"
hypotheses: []
```

{title}.
"""

QUESTIONS_HEAD = ("---\ntype: collection\nholds: question\n---\n\n# Questions\n\n"
                  "The key questions the engagement must answer.\n\n")

# The three synthetic questions the extract-observations tests and fixtures use.
OBSERVE_QUESTIONS = [
    {"id": "Q-001", "title": "What does fulfilment cost per order"},
    {"id": "Q-002", "title": "Is north-site staffing enough"},
    {"id": "Q-003", "title": "Why is fulfilment slow"},
]


def questions_md(questions) -> str:
    """A `00-charter/questions.md` holding `questions` ({id, title, status}); none → the seed text."""
    import json as _json

    if not questions:
        return QUESTIONS_HEAD + "No questions yet.\n"
    return QUESTIONS_HEAD + "\n".join(
        QUESTION_ENTRY.format(id=q["id"], title=q["title"], title_json=_json.dumps(q["title"]),
                              status=q.get("status", "active"))
        for q in questions)
