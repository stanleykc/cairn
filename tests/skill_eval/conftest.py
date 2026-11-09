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
DOCUMENTS = FIXTURES / "documents"
INGEST_FIXTURES = REPO / "tests" / "fixtures" / "ingest"
CANARY = "CANARY-7f3a"
BRIEF = f"""# Kickoff brief (synthetic)

Reference {CANARY}. The client wants faster order-to-ship in the north DCs, a final
readout on 2026-12-04, and no capital spend this year.
"""
TEXT_SUFFIXES = (".md", ".markdown", ".txt")


def doc_canary(name: str) -> str:
    """A per-document canary line, appended to text documents copied into a test copy."""
    return f"CANARY-DOC-{Path(name).stem}"


def copy_documents(root: Path, names) -> None:
    """Copy synthetic documents into `10-sources/raw/`; text ones gain their canary line."""
    raw = root / "10-sources" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for name in names or ():
        data = (DOCUMENTS / name).read_bytes()
        if name.endswith(TEXT_SUFFIXES):
            data += f"\nReference {doc_canary(name)}.\n".encode()
        (raw / name).write_bytes(data)


def write_extracted_stubs(root: Path, stubs) -> None:
    """Minimal ingest source records: only `id`, `raw_file` and `restricted` matter to charter."""
    folder = root / "10-sources" / "extracted"
    folder.mkdir(parents=True, exist_ok=True)
    for stub in stubs or ():
        (folder / f"{stub['id']}.md").write_text(
            f'---\nid: "{stub["id"]}"\ntype: source\nraw_file: "{stub["raw_file"]}"\n'
            f"restricted: {'true' if stub.get('restricted') else 'false'}\n---\n\n"
            f"Reference {CANARY}.\n")

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

    def make(fixture: str = "fresh", model_use: str | None = None, edits=(), scenario=None) -> Path:
        scenario = scenario or {}
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
            set_model_use(root, model_use, scenario.get("model_use_notes", ""))
        for rel, old, new in edits:
            path = root / rel
            assert old in path.read_text(), (rel, old)
            path.write_text(path.read_text().replace(old, new, 1))
        for rel in ("10-sources/raw/brief.md", "10-sources/extracted/S-001.md"):
            (root / rel).write_text(BRIEF)
        copy_documents(root, scenario.get("documents"))
        write_extracted_stubs(root, scenario.get("extracted"))
        for rel, text in (scenario.get("outside_files") or {}).items():
            path = work / rel  # relative to the folder that holds the engagement
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
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


# --- extract-observations (feature 005) -----------------------------------------------------

OBSERVE_FIXTURES = REPO / "tests" / "fixtures" / "observe"
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


def questions_md(questions) -> str:
    """A `00-charter/questions.md` holding `questions` ({id, title, status}); none → the seed text."""
    head = ("---\ntype: collection\nholds: question\n---\n\n# Questions\n\n"
            "The key questions the engagement must answer.\n\n")
    if not questions:
        return head + "No questions yet.\n"
    return head + "\n".join(
        QUESTION_ENTRY.format(id=q["id"], title=q["title"], title_json=json.dumps(q["title"]),
                              status=q.get("status", "active"))
        for q in questions)


def set_front_fields(text: str, fields: dict) -> str:
    """Replace (or add) flat front matter fields; values are written as YAML/JSON scalars."""
    for key, value in fields.items():
        rendered = json.dumps(value) if isinstance(value, (str, list)) else str(value).lower()
        if re.search(rf"^{re.escape(key)}:", text, re.M):
            text = re.sub(rf"^{re.escape(key)}:.*$", lambda _: f"{key}: {rendered}", text, count=1, flags=re.M)
        else:
            text = text.replace("\n---\n", f"\n{key}: {rendered}\n---\n", 1)
    return text


@pytest.fixture
def make_observe_engagement(tmp_path, git_env):
    """Build a committed synthetic engagement for an `extract-observations` scenario.

    Scenario keys used here: `fixture` (a case in `tests/fixtures/observe/`, e.g. `golden/us1`),
    `model_use`, `code_name` ("" removes the code name), `questions` (list of {id, title,
    status}, written to `00-charter/questions.md`; `[]` leaves no questions), `existing`
    (engagement-relative path → text, or → {from: <case-relative path>, fields: {...}}),
    `source_edits` (S-ID → front matter overrides, e.g. {restricted: true}), `source_appends`
    (S-ID → a line added at the end of its content region, e.g. a canary),
    `source_files` (engagement-relative path → text, for test-time sources holding canaries)
    and `outside_files` (path relative to the folder holding the engagement → text).
    """

    def make(scenario: dict) -> Path:
        work = tmp_path / "work"
        work.mkdir()
        case = OBSERVE_FIXTURES / scenario["fixture"]
        record = yaml.safe_load((case / "engagement.md").read_text().split("---\n")[1])
        if "code_name" in scenario:
            record["client_code_name"] = scenario["code_name"]
        cairn(*_init_args(record), cwd=work, env=git_env)
        [root] = [p for p in work.iterdir() if p.is_dir()]
        shutil.copytree(case, root, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("expected", "drafts*.json"))
        if "code_name" in scenario:
            path = root / "engagement.md"
            path.write_text(set_front_fields(path.read_text(), {"client_code_name": scenario["code_name"]}))
        if scenario.get("model_use"):
            set_model_use(root, scenario["model_use"], scenario.get("model_use_notes", ""))
        if "questions" in scenario:
            (root / "00-charter" / "questions.md").write_text(questions_md(scenario["questions"]))
        for rel, text in (scenario.get("source_files") or {}).items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        for source_id, fields in (scenario.get("source_edits") or {}).items():
            path = root / "10-sources" / "extracted" / f"{source_id}.md"
            path.write_text(set_front_fields(path.read_text(), fields))
        for source_id, line in (scenario.get("source_appends") or {}).items():
            path = root / "10-sources" / "extracted" / f"{source_id}.md"
            text = path.read_text()
            assert "<!-- cairn:content:end -->" in text, source_id
            path.write_text(text.replace("<!-- cairn:content:end -->", f"{line}\n<!-- cairn:content:end -->", 1))
        for rel, spec in (scenario.get("existing") or {}).items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(spec, dict):
                text = set_front_fields((case / spec["from"]).read_text(), spec.get("fields", {}))
            else:
                text = spec
            path.write_text(text)
        for rel, text in (scenario.get("outside_files") or {}).items():
            path = work / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git("init", "-q", cwd=root, env=git_env)
        git("add", "-A", cwd=root, env=git_env)
        git("commit", "-q", "-m", "Synthetic engagement for skill evaluation", cwd=root, env=git_env)
        return root

    return make
