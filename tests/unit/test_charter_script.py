"""Unit tests for the `charter` skill's helper script (contracts/charter-script.md).

Only synthetic names are used (Principle VIII). Fixtures are always copied to `tmp_path`.
"""

import ast
import builtins
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import layout
from conftest import PACKAGE_ASSETS

SCRIPT = PACKAGE_ASSETS / "skills" / "charter" / "scripts" / "charter.py"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "charter"
NOT_IN_ENGAGEMENT = (
    "Not inside a Cairn engagement. Create one with `cairn init`, then run `charter` "
    "from inside it."
)


@pytest.fixture(scope="module")
def charter():
    spec = importlib.util.spec_from_file_location("charter_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # keep the assets clean
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


def copy_fixture(tmp_path: Path, name: str) -> Path:
    dest = tmp_path / name
    shutil.copytree(FIXTURES / name, dest)
    return dest


def run(root, *args, cwd=None, script=SCRIPT, use_root=True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(script)]
    if use_root:
        cmd += ["--root", str(root)]
    return subprocess.run(
        cmd + [str(a) for a in args], cwd=cwd or root, capture_output=True, text=True
    )


def run_json(root, *args, expect=0) -> dict:
    result = run(root, *args)
    assert result.returncode == expect, result.stderr + result.stdout
    return json.loads(result.stdout)


def append(path: Path, text: str) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text)


def entry(id_: str, title="Synthetic item", **fields) -> str:
    """A charter entry in the template form, with every standard field filled."""
    type_ = {"Q": "question", "H": "hypothesis", "A": "assumption"}[id_[0]]
    base = {
        "id": f'"{id_}"', "type": type_, "title": f'"{title}"', "status": "proposed",
        "origin": "consultant-note", "confidence": "medium",
        "confidence_reason": '"stated by the consultant"', "inference_confirmed": "false",
        "audience": "internal", "supports": "[]", "contradicts": "[]", "derived_from": "[]",
        "supersedes": "[]", "clarifies": "[]", "change_reason": '""', "change_trigger": '""',
        "created": '"2026-11-03"',
    }
    base.update({
        "question": {"priority": '"medium"', "raised_by": '"Test Lead"', "hypotheses": "[]"},
        "hypothesis": {"question": '""', "confirm_if": '"a"', "reject_if": '"b"',
                       "supported_by": "[]", "contradicted_by": "[]"},
        "assumption": {"basis": '"experience"', "questions": "[]"},
    }[type_])
    base.update(fields)
    body = "\n".join(f"{k}: {v}" for k, v in base.items() if v is not None)
    return f"\n## {id_}: {title}\n\n```yaml\n{body}\n```\n\nSynthetic text.\n"


@pytest.fixture
def empty(tmp_path) -> Path:
    return copy_fixture(tmp_path, "empty")


# --- Discovery (R5) ------------------------------------------------------------


def test_discovery_walks_up_from_subfolder(empty):
    result = run(empty, "status", cwd=empty / "00-charter", use_root=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["engagement"]["root"] == str(empty.resolve())


def test_discovery_falls_back_to_script_location(empty, tmp_path):
    installed = empty / ".claude" / "skills" / "charter" / "scripts" / "charter.py"
    installed.parent.mkdir(parents=True)
    shutil.copy(SCRIPT, installed)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    result = run(None, "status", cwd=elsewhere, script=installed, use_root=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["engagement"]["root"] == str(empty.resolve())


def test_outside_engagement_exits_2(tmp_path):
    copy = tmp_path / "c.py"
    shutil.copy(SCRIPT, copy)
    outside = tmp_path / "outside"
    outside.mkdir()
    result = run(None, "status", cwd=outside, script=copy, use_root=False)
    assert result.returncode == 2
    assert result.stderr.strip() == NOT_IN_ENGAGEMENT
    assert result.stdout == ""


def test_shallow_script_path_has_no_traceback(charter, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert charter.main(["status"], script_path=Path("/c.py")) == 2
    err = capsys.readouterr().err
    assert err.strip() == NOT_IN_ENGAGEMENT
    assert "Traceback" not in err


def test_root_that_is_not_an_engagement(tmp_path):
    result = run(tmp_path, "status")
    assert result.returncode == 2
    assert NOT_IN_ENGAGEMENT in result.stderr


def test_bad_arguments_exit_3(empty):
    assert run(empty, "bogus").returncode == 3
    assert run(empty, "model-use", "--set", "maybe").returncode == 3
    assert run(empty, "refs").returncode == 3
    assert run(empty, "refs", "not-an-id").returncode == 3


def test_version():
    result = subprocess.run([sys.executable, str(SCRIPT), "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "charter.py 0.2.0"


# --- Parser (R4) -------------------------------------------------------------------


def test_parse_scalars_and_lists(charter):
    lines = [
        'a: "quoted # not a comment"  # comment',
        "b: bare value  # comment",
        "c: 'single ''quoted'''",
        'd: ["Q-001", "Q-002"]',
        "e: [Q-001]",
        "f: []",
        "g:",
        "  - Q-001",
        "  - \"Q-002\"",
        "h: 2026-11-03",
        "# a comment line",
        "",
        'i: ""',
    ]
    fields, errors = charter.parse_mapping(lines, 1)
    assert errors == []
    assert fields == {
        "a": "quoted # not a comment", "b": "bare value", "c": "single 'quoted'",
        "d": ["Q-001", "Q-002"], "e": ["Q-001"], "f": [], "g": ["Q-001", "Q-002"],
        "h": "2026-11-03", "i": "",
    }


@pytest.mark.parametrize("line", [
    'a: "unterminated', "a: [Q-001, Q-002", "a: [[Q-001]]", "  nested: value",
    "just text", 'a: "x" trailing', "a: {b: c}",
])
def test_parse_reports_unreadable_lines(charter, line):
    fields, errors = charter.parse_mapping(["ok: 1", line], 10)
    assert fields["ok"] == "1"
    assert errors and errors[0][0] == 11


def test_parse_file_entries(charter):
    text = (
        "---\ntype: collection\nholds: question\n---\n\n# Questions\n"
        + entry("Q-001", "First")
        + "\n## Q-002: Second\n\n```yaml\nid: \"Q-002\"\nstatus: [oops\n```\n"
        + "\n## Notes\n\nNot an entry.\n"
    )
    parsed = charter.parse_file(text, "00-charter/questions.md")
    assert parsed["front"] == {"type": "collection", "holds": "question"}
    assert [e["id"] for e in parsed["entries"]] == ["Q-001", "Q-002"]
    first = parsed["entries"][0]
    assert first["title"] == "First" and first["fields"]["priority"] == "medium"
    assert first["file"] == "00-charter/questions.md" and first["line"] == 8
    [problem] = parsed["problems"]
    assert problem["code"] == "unparseable" and problem["id"] == "Q-002"
    assert text.splitlines()[problem["line"] - 1] == "status: [oops"


def test_parse_single_object_file(charter):
    text = '---\nid: "O-014"\ntype: observation\nquestions: ["Q-002"]\n---\n\nBody Q-009.\n'
    parsed = charter.parse_file(text, "30-observations/O-014.md")
    assert parsed["front"]["id"] == "O-014"
    assert parsed["front"]["questions"] == ["Q-002"]
    assert parsed["entries"] == []


# --- ID assignment (R9) --------------------------------------------------------------


def next_ids(root) -> dict:
    return run_json(root, "status")["next_ids"]


def test_next_ids_with_gaps_and_hand_entries(empty):
    append(empty / "00-charter/questions.md", entry("Q-001") + entry("Q-005"))
    append(empty / "00-charter/hypotheses.md", entry("H-002", question='"Q-001"'))
    assert next_ids(empty) == {"Q": "Q-006", "H": "H-003", "A": "A-001"}


def test_next_ids_count_mentions_elsewhere(empty):
    (empty / "30-observations").mkdir()
    (empty / "30-observations" / "O-001.md").write_text(
        '---\nid: "O-001"\nquestions: ["Q-012"]\n---\n'
    )
    append(empty / "60-log/changelog.md", "2026-11-03 · A-007 · reject · gone · rethinking\n")
    assert next_ids(empty) == {"Q": "Q-013", "H": "H-001", "A": "A-008"}


def test_next_id_grows_to_four_digits(empty):
    append(empty / "00-charter/questions.md", entry("Q-999"))
    assert next_ids(empty)["Q"] == "Q-1000"


def test_ids_in_sources_are_ignored(empty):
    extracted = empty / "10-sources" / "extracted"
    extracted.mkdir(parents=True)
    (extracted / "S-001.md").write_text("Mentions Q-050 and H-020.\n")
    (empty / "_templates").mkdir()
    (empty / "_templates" / "question.md").write_text("Example Q-077.\n")
    assert next_ids(empty) == {"Q": "Q-001", "H": "H-001", "A": "A-001"}


# --- 10-sources/ is never opened (R6) ---------------------------------------------


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permissions")
def test_unreadable_sources_canary(empty):
    raw = empty / "10-sources" / "raw"
    raw.mkdir(parents=True)
    canary = raw / "canary.md"
    canary.write_text("CANARY-7f3a Q-500\n")
    canary.chmod(0o000)
    try:
        for args in (("status",), ("check",), ("refs", "Q-001")):
            result = run(empty, *args)
            assert result.returncode == 0, result.stderr
            assert "CANARY" not in result.stdout
    finally:
        canary.chmod(0o644)


def test_sources_never_touched_in_process(charter, empty, monkeypatch, capsys):
    (empty / "10-sources" / "raw").mkdir(parents=True)
    (empty / "10-sources" / "raw" / "brief.md").write_text("CANARY-7f3a\n")
    touched = []

    def spy(name, original):
        def wrapper(*args, **kwargs):
            touched.append(str(args[0]))
            return original(*args, **kwargs)
        return wrapper

    monkeypatch.setattr(os, "walk", spy("walk", os.walk))
    monkeypatch.setattr(os, "scandir", spy("scandir", os.scandir))
    monkeypatch.setattr(os, "listdir", spy("listdir", os.listdir))
    monkeypatch.setattr(builtins, "open", spy("open", builtins.open))
    monkeypatch.setattr(Path, "read_text", spy("read_text", Path.read_text))
    monkeypatch.setattr(Path, "read_bytes", spy("read_bytes", Path.read_bytes))
    monkeypatch.setattr(Path, "iterdir", spy("iterdir", Path.iterdir))
    for args in (["status"], ["check"], ["refs", "Q-001"]):
        assert charter.main(["--root", str(empty), *args]) == 0
    capsys.readouterr()
    assert touched, "the spies saw no file access"
    assert not [p for p in touched if "10-sources" in p]


def test_content_folders_match_layout(charter):
    expected = tuple(
        f for f in layout.CANONICAL_FOLDERS
        if not f.startswith("10-sources") and f != "_templates"
    )
    assert charter.CONTENT_FOLDERS == expected


# --- Python 3.9, standard library only (R3) ------------------------------------------


def test_python_39_syntax():
    source = SCRIPT.read_text()
    ast.parse(source, feature_version=(3, 9))
    assert "from __future__ import annotations" in source
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "cairn" not in imported
    assert imported <= set(sys.stdlib_module_names)


def _python39():
    for candidate in ("/usr/bin/python3", shutil.which("python3.9")):
        if not candidate or not Path(candidate).exists():
            continue
        out = subprocess.run([candidate, "-c", "import sys; print(sys.version_info[:2])"],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip() == "(3, 9)":
            return candidate
    return None


@pytest.mark.skipif(_python39() is None, reason="no Python 3.9 interpreter on this machine")
def test_runs_on_python_39(empty):
    result = subprocess.run([_python39(), str(SCRIPT), "--root", str(empty), "status"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["charter"]["state"] == "empty"


# --- US1: status and check ----------------------------------------------------------


@pytest.fixture
def drafted(tmp_path) -> Path:
    return copy_fixture(tmp_path, "drafted")


def codes(result: dict) -> list:
    return sorted(p["code"] for p in result["problems"])


def replace(path: Path, old: str, new: str, count=1) -> None:
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new, count))


def test_state_transitions(empty):
    assert run_json(empty, "status")["charter"]["state"] == "empty"
    replace(empty / "00-charter/scope.md",
            "What the client needs from this engagement, in a few bullet points.",
            "- Cut order-to-ship time by 30%.")
    assert run_json(empty, "status")["charter"]["state"] == "draft"
    replace(empty / "00-charter/scope.md", "charter_status: draft", "charter_status: approved")
    assert run_json(empty, "status")["charter"]["state"] == "approved"


def test_state_draft_with_items_only(empty):
    append(empty / "00-charter/questions.md", entry("Q-001"))
    status = run_json(empty, "status")
    assert status["charter"]["state"] == "draft"
    assert status["charter"]["charter_status"] == "draft"


def test_charter_status_defaults_to_draft(empty):
    path = empty / "00-charter/scope.md"
    path.write_text("\n".join(l for l in path.read_text().split("\n")
                              if not l.startswith(("charter_status", "approved_"))))
    charter = run_json(empty, "status")["charter"]
    assert (charter["charter_status"], charter["approved_on"], charter["approved_by"]) == ("draft", "", "")


def test_scope_sections_seed_020(empty):
    sections = run_json(empty, "status")["charter"]["scope_sections"]
    assert sections == {s: "empty" for s in
                        ("Objectives", "In scope", "Out of scope", "Deliverables", "Timeline", "Constraints")}


SCOPE_010 = """---
type: charter-scope
model_use: unconfirmed  # copy for reading; engagement.md is authoritative
---

# Scope

## Objectives

What the client needs from this engagement, in a few bullet points.

## Boundaries

What is in scope and, just as important, what is not.

## Deliverables

What will be handed to the client, and in what form.

## Timeline

Key dates: kick-off, interviews, readouts, final delivery.

## Model use

Current policy: **unconfirmed**. This is what the client agreement allows to be sent to
external AI services (`allowed`, `restricted` or `unconfirmed`). The authoritative value is
in `engagement.md`; change it there first and keep this copy in line.
"""


def test_scope_sections_seed_010(empty):
    (empty / "00-charter/scope.md").write_text(SCOPE_010)
    status = run_json(empty, "status")
    assert status["charter"]["scope_sections"] == {
        "Objectives": "empty", "In scope": "missing", "Out of scope": "missing",
        "Deliverables": "empty", "Timeline": "empty", "Constraints": "missing",
    }
    assert status["charter"]["state"] == "empty"
    assert status["charter"]["charter_status"] == "draft"


def test_counts_on_drafted(drafted):
    charter = run_json(drafted, "status")["charter"]
    assert (charter["stakeholders"], charter["lenses"], charter["criteria"]) == (2, 4, 2)
    assert all(v == "filled" for v in charter["scope_sections"].values())


def test_items_have_titles_for_charter_entries_only(tmp_path):
    root = copy_fixture(tmp_path, "approved")
    status = run_json(root, "status")
    assert [i["id"] for i in status["items"]] == [
        "Q-001", "Q-002", "Q-003", "Q-004", "H-001", "H-002", "H-003", "A-001", "A-002"]
    q2 = status["items"][1]
    assert q2["title"] == "Which steps drive most of the delay"
    assert q2["links"] == {"hypotheses": ["H-002", "H-003"]}
    assert q2["file"] == "00-charter/questions.md" and q2["priority"] == "high"
    assert status["items"][5]["links"] == {"question": "Q-002"}
    assert status["items"][7]["links"] == {"questions": ["Q-001"]}
    out = run(root, "status").stdout
    assert "Pickup waits averaged" not in out and "Carrier pickup timing" not in out


def test_drafted_is_clean(drafted):
    result = run_json(drafted, "check")
    assert result == {"ok": True, "problems": [], "checked": {"Q": 3, "H": 2, "A": 1}}


def check_codes(root) -> list:
    result = run(root, "check")
    data = json.loads(result.stdout)
    assert result.returncode == (1 if data["problems"] else 0)
    assert data["ok"] is (not data["problems"])
    return codes(data)


def test_duplicate_id(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-002", hypotheses='["H-002"]'))
    assert check_codes(drafted) == ["duplicate-id"]


def test_malformed_heading(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-004").replace("## Q-004:", "## Q-7:"))
    assert check_codes(drafted) == ["malformed-id"]


def test_malformed_heading_id_differs_from_field(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-004", id='"Q-005"'))
    assert check_codes(drafted) == ["malformed-id"]


def test_malformed_prefix_not_held_by_file(drafted):
    append(drafted / "00-charter/questions.md", entry("A-002"))
    assert check_codes(drafted) == ["malformed-id"]


def test_unparseable(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-004", status='"proposed'))
    result = json.loads(run(drafted, "check").stdout)
    assert codes(result) == ["unparseable"]
    assert result["problems"][0]["id"] == "Q-004" and result["problems"][0]["line"]


def test_missing_field(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-004", raised_by=None, confidence=None))
    result = json.loads(run(drafted, "check").stdout)
    assert codes(result) == ["missing-field"]
    assert "confidence" in result["problems"][0]["detail"]
    assert "raised_by" in result["problems"][0]["detail"]


def test_fields_added_in_020_may_be_missing(drafted):
    append(drafted / "00-charter/questions.md",
           entry("Q-004", change_reason=None, change_trigger=None, hypotheses='["H-003"]'))
    append(drafted / "00-charter/hypotheses.md",
           entry("H-003", question='"Q-004"', confirm_if=None, reject_if=None,
                 change_reason=None, change_trigger=None))
    assert check_codes(drafted) == []


@pytest.mark.parametrize("field,value", [
    ("status", "done"), ("origin", "guess"), ("confidence", "certain"), ("audience", "public"),
    ("priority", "urgent"), ("change_trigger", "new evidence"), ("confidence_reason", '""'),
    ("confidence", '""'),
])
def test_bad_value(drafted, field, value):
    append(drafted / "00-charter/questions.md", entry("Q-004", **{field: value}))
    assert check_codes(drafted) == ["bad-value"]


def test_empty_priority_is_allowed(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-004", priority='""'))
    assert check_codes(drafted) == []


def test_client_ready(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-004", audience="client-ready"))
    assert check_codes(drafted) == ["client-ready"]


def test_cited_source_in_field(drafted):
    append(drafted / "00-charter/assumptions.md", entry("A-002", supports='["S-001"]'))
    assert check_codes(drafted) == ["cited-source"]


def test_cited_source_origin(drafted):
    append(drafted / "00-charter/assumptions.md", entry("A-002", origin="client-document"))
    assert check_codes(drafted) == ["cited-source"]


@pytest.mark.parametrize("question", ['""', '["Q-001", "Q-002"]', '"Q-099"', '"H-001"'])
def test_hypothesis_question(drafted, question):
    append(drafted / "00-charter/hypotheses.md", entry("H-003", question=question))
    assert check_codes(drafted) == ["hypothesis-question"]


def test_one_way_link_hypothesis_not_listed(drafted):
    append(drafted / "00-charter/hypotheses.md", entry("H-003", question='"Q-003"'))
    result = json.loads(run(drafted, "check").stdout)
    assert codes(result) == ["one-way-link"]
    assert result["problems"][0]["id"] == "H-003"
    assert result["problems"][0]["detail"] == "question Q-003 does not list H-003"


def test_one_way_link_question_lists_other_hypothesis(drafted):
    replace(drafted / "00-charter/questions.md", 'hypotheses: []', 'hypotheses: ["H-001"]')
    result = json.loads(run(drafted, "check").stdout)
    assert codes(result) == ["one-way-link"]
    assert result["problems"][0]["id"] == "Q-003"


def test_broken_link(drafted):
    replace(drafted / "00-charter/assumptions.md", 'questions: ["Q-001"]', 'questions: ["Q-001", "Q-042"]')
    result = json.loads(run(drafted, "check").stdout)
    assert codes(result) == ["broken-link"]
    assert "Q-042" in result["problems"][0]["detail"]


def test_broken_link_in_question_hypotheses(drafted):
    replace(drafted / "00-charter/questions.md", 'hypotheses: []', 'hypotheses: ["H-009"]')
    assert check_codes(drafted) == ["broken-link"]


def test_problems_shape(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-004", audience="client-ready"))
    [problem] = run_json(drafted, "status")["problems"]
    assert set(problem) == {"code", "id", "file", "line", "detail"}
    assert problem["file"] == "00-charter/questions.md"
    lines = (drafted / problem["file"]).read_text().splitlines()
    assert lines[problem["line"] - 1].startswith("## Q-004:")


def test_unparseable_entry_does_not_cause_link_problems(drafted):
    replace(drafted / "00-charter/hypotheses.md", 'question: "Q-001"', 'question: "Q-001')
    assert check_codes(drafted) == ["unparseable"]


# --- US2: model-use, mismatch, real-name leak --------------------------------------

TODAY = __import__("datetime").date.today().isoformat()


def front_line(path: Path, key: str) -> str:
    return next(l for l in path.read_text().splitlines() if l.startswith(f"{key}:"))


def test_model_use_sets_both_files(empty):
    result = run_json(empty, "model-use", "--set", "restricted", "--notes", "No transcripts to external AI")
    assert result == {"model_use": "restricted", "model_use_notes": "No transcripts to external AI",
                      "changed": ["engagement.md", "00-charter/scope.md", "60-log/changelog.md"]}
    record, scope = empty / "engagement.md", empty / "00-charter/scope.md"
    assert front_line(record, "model_use") == "model_use: restricted  # allowed | restricted | unconfirmed"
    assert front_line(record, "model_use_notes") == (
        'model_use_notes: "No transcripts to external AI"  # specific restrictions, free text')
    assert front_line(scope, "model_use") == (
        "model_use: restricted  # copy for reading; engagement.md is authoritative")
    assert front_line(scope, "model_use_notes") == 'model_use_notes: "No transcripts to external AI"'
    text = scope.read_text()
    assert "Current policy: **restricted**.\nRestrictions: No transcripts to external AI.\n" in text
    changelog = (empty / "60-log/changelog.md").read_text()
    assert "No changes yet." not in changelog
    assert changelog.rstrip().endswith(
        f"{TODAY} · model-use · model-use · unconfirmed → restricted (No transcripts to external AI) · -")
    assert check_codes(empty) == []


def test_model_use_repeat_writes_nothing(empty):
    run_json(empty, "model-use", "--set", "allowed")
    before = {p: p.read_bytes() for p in empty.rglob("*.md")}
    assert run_json(empty, "model-use", "--set", "allowed")["changed"] == []
    assert {p: p.read_bytes() for p in empty.rglob("*.md")} == before


def test_model_use_second_event_appends(empty):
    run_json(empty, "model-use", "--set", "allowed")
    run_json(empty, "model-use", "--set", "restricted", "--notes", "Decks only")
    lines = [l for l in (empty / "60-log/changelog.md").read_text().splitlines() if l.startswith(TODAY)]
    assert lines == [
        f"{TODAY} · model-use · model-use · unconfirmed → allowed · -",
        f"{TODAY} · model-use · model-use · allowed → restricted (Decks only) · -",
    ]


def test_model_use_adds_missing_lines(empty):
    record, scope = empty / "engagement.md", empty / "00-charter/scope.md"
    for path in (record, scope):
        path.write_text("\n".join(l for l in path.read_text().split("\n")
                                  if not l.startswith(("model_use_notes:", "Restrictions:"))))
    run_json(empty, "model-use", "--set", "allowed", "--notes", "All fine")
    for path in (record, scope):
        lines = path.read_text().splitlines()
        at = next(i for i, l in enumerate(lines) if l.startswith("model_use:"))
        assert lines[at + 1] == 'model_use_notes: "All fine"'
    lines = scope.read_text().splitlines()
    at = lines.index("Current policy: **allowed**.")
    assert lines[at + 1] == "Restrictions: All fine."


def test_model_use_upgrades_010_scope(empty):
    scope = empty / "00-charter/scope.md"
    scope.write_text(SCOPE_010)
    run_json(empty, "model-use", "--set", "restricted", "--notes", "No audio")
    text = scope.read_text()
    assert ("Current policy: **restricted**.\nRestrictions: No audio.\n\nThis is what the client "
            "agreement allows to be sent to\nexternal AI services") in text
    assert front_line(scope, "model_use_notes") == 'model_use_notes: "No audio"'
    assert check_codes(empty) == []


def test_model_use_without_section_writes_nothing(empty):
    scope = empty / "00-charter/scope.md"
    scope.write_text(scope.read_text().replace("## Model use", "## Policy"))
    before = {rel: (empty / rel).read_bytes()
              for rel in ("engagement.md", "00-charter/scope.md", "60-log/changelog.md")}
    result = run(empty, "model-use", "--set", "allowed")
    assert result.returncode == 3
    assert "Model use" in result.stderr
    assert {rel: (empty / rel).read_bytes() for rel in before} == before


def test_model_use_notes_round_trip(charter, empty):
    notes = 'Say "no" to transcripts · decks OK \\ maybe'
    run_json(empty, "model-use", "--set", "restricted", "--notes", notes)
    assert run_json(empty, "status")["engagement"]["model_use_notes"] == notes
    for rel in ("engagement.md", "00-charter/scope.md"):
        lines = (empty / rel).read_text().splitlines()
        fm, _ = charter.split_front_matter(lines)
        assert charter.parse_mapping(fm, 2)[0]["model_use_notes"] == notes
    last = (empty / "60-log/changelog.md").read_text().rstrip().splitlines()[-1]
    assert last.count(" · ") == 4
    assert "decks OK" in last and "transcripts - decks" in last
    assert check_codes(empty) == []


def test_model_use_mismatch(drafted):
    replace(drafted / "00-charter/scope.md", "model_use: restricted", "model_use: allowed")
    assert check_codes(drafted) == ["model-use-mismatch"]


def test_model_use_mismatch_missing_notes_line_counts_as_empty(empty):
    scope = empty / "00-charter/scope.md"
    scope.write_text("\n".join(l for l in scope.read_text().split("\n") if not l.startswith("model_use_notes:")))
    assert check_codes(empty) == []


@pytest.fixture
def northwind(tmp_path) -> Path:
    return copy_fixture(tmp_path, "codename")


@pytest.mark.parametrize("rel", ["00-charter/questions.md", "60-log/changelog.md"])
def test_real_name_leak(northwind, rel):
    append(northwind / rel, "\nNotes from the GLOBEX kickoff.\n")
    result = run(northwind, "check")
    assert result.returncode == 1
    [problem] = json.loads(result.stdout)["problems"]
    assert (problem["code"], problem["file"]) == ("real-name-leak", rel)
    assert "globex" not in result.stdout.lower()


def test_codename_output_never_has_real_name(northwind):
    append(northwind / "00-charter/questions.md", entry("Q-002", title="Globex pricing"))
    for args in (("status",), ("check",), ("refs", "Q-001", "H-001")):
        result = run(northwind, *args)
        assert result.stdout, args
        assert "globex" not in result.stdout.lower(), args
    status = run_json(northwind, "status")
    assert status["engagement"]["client_label"] == "Northwind"
    assert status["engagement"]["uses_code_name"] is True


def test_no_leak_check_without_code_name(drafted):
    append(drafted / "00-charter/questions.md", "\nAcme said so.\n")
    assert check_codes(drafted) == []


# --- US3: approval ------------------------------------------------------------------


@pytest.fixture
def approved(tmp_path) -> Path:
    return copy_fixture(tmp_path, "approved")


def test_proposed_since_approval(approved, drafted):
    assert run_json(approved, "status")["proposed_since_approval"] == 0
    append(approved / "00-charter/questions.md", entry("Q-005") + entry("Q-006"))
    assert run_json(approved, "status")["proposed_since_approval"] == 2
    assert run_json(drafted, "status")["proposed_since_approval"] == 0


def test_reject_state(drafted):
    append(drafted / "00-charter/questions.md", entry("Q-004", status="rejected"))
    assert check_codes(drafted) == ["reject-state"]
    append(drafted / "00-charter/questions.md",
           entry("Q-005", status="rejected", change_reason='"too broad"', change_trigger="rethinking"))
    assert check_codes(drafted) == ["reject-state"]


def test_approved_unconfirmed(approved):
    for rel in ("engagement.md", "00-charter/scope.md"):
        replace(approved / rel, "model_use: allowed", "model_use: unconfirmed")
    assert check_codes(approved) == ["approved-unconfirmed"]


# --- US4: refs, pending revisions, supersede-state -----------------------------------


def refs(root, *ids) -> dict:
    return {k: [(r["id"], r["field"]) for r in v] for k, v in run_json(root, "refs", *ids)["refs"].items()}


def test_refs(approved):
    assert refs(approved, "Q-002", "H-002", "A-001") == {
        "Q-002": [("H-002", "question"), ("H-003", "question"), ("O-014", "questions"),
                  ("F-003", "questions")],
        "H-002": [("Q-002", "hypotheses"), ("O-014", "supports")],
        "A-001": [("F-003", "derived_from")],
    }
    files = [r["file"] for r in run_json(approved, "refs", "Q-002")["refs"]["Q-002"]]
    assert files == ["00-charter/hypotheses.md", "00-charter/hypotheses.md",
                     "30-observations/O-014.md", "40-synthesis/findings/F-003.md"]


def test_refs_ignore_body_text_changelog_and_own_id(approved):
    append(approved / "60-log/changelog.md", "2026-11-10 · Q-004 · clarify · wording · rethinking\n")
    # O-014's body mentions H-001; the changelog mentions Q-004; F-003's own id is F-003
    assert refs(approved, "H-001", "Q-004", "F-003", "Q-404") == {
        "H-001": [("Q-001", "hypotheses")], "Q-004": [], "F-003": [], "Q-404": [],
    }


def test_refs_never_print_other_objects_text(approved):
    out = run(approved, "refs", "Q-002", "H-002", "A-001").stdout
    for text in ("Pickup waits averaged", "Carrier pickup timing", "sheet 2", "Fixing pickup"):
        assert text not in out


def test_refs_cover_decisions_and_inbox(approved):
    (approved / "_inbox").mkdir()
    (approved / "_inbox" / "F-009.md").write_text('---\nid: "F-009"\nquestions: ["Q-003"]\n---\n')
    append(approved / "60-log/decisions.md",
           '\n## D-001: Pick a scope\n\n```yaml\nid: "D-001"\ndecides: ["Q-003"]\n```\n')
    assert refs(approved, "Q-003") == {
        "Q-003": [("A-002", "questions"), ("D-001", "decides"), ("F-009", "questions")]}


def test_pending_revisions(tmp_path):
    root = copy_fixture(tmp_path, "revised")
    assert run_json(root, "status")["pending_revisions"] == [{"new": "H-005", "old": "H-003"}]


def test_supersede_state(tmp_path):
    root = copy_fixture(tmp_path, "revised")
    assert check_codes(root) == []
    # no successor: nothing lists H-002 in `supersedes` any more
    replace(root / "00-charter/hypotheses.md", 'supersedes: ["H-002"]', "supersedes: []")
    assert check_codes(root) == ["supersede-state"]


def test_supersede_state_without_reason(tmp_path):
    root = copy_fixture(tmp_path, "revised")
    path = root / "00-charter/hypotheses.md"
    text = path.read_text()
    start = text.index("## H-002:")
    end = text.index("## H-003:")
    block = text[start:end].replace(
        'change_reason: "narrowed to weekday pickups after the week 44 data"', 'change_reason: ""')
    path.write_text(text[:start] + block + text[end:])
    assert check_codes(root) == ["supersede-state"]


# --- US5: gaps --------------------------------------------------------------------------


def gaps(root) -> list:
    return [(g["code"], g.get("id") or g.get("section")) for g in run_json(root, "status")["gaps"]]


def test_gap_codes(drafted):
    append(drafted / "00-charter/hypotheses.md",
           entry("H-003", question='"Q-003"', confirm_if='""', reject_if='""'))
    replace(drafted / "00-charter/questions.md", "hypotheses: []", 'hypotheses: ["H-003"]')
    append(drafted / "00-charter/assumptions.md", entry("A-002", basis='""'))
    assert gaps(drafted) == [
        ("hypothesis-no-reject", "H-003"), ("hypothesis-no-confirm", "H-003"),
        ("assumption-no-basis", "A-002"),
    ]


def test_gaps_ignore_rejected_and_superseded(drafted):
    append(drafted / "00-charter/questions.md",
           entry("Q-004", status="rejected", change_reason='"dropped"', change_trigger="rethinking"))
    append(drafted / "00-charter/assumptions.md",
           entry("A-002", basis='""', status="rejected", change_reason='"dropped"', change_trigger="rethinking"))
    assert gaps(drafted) == [("question-no-hypothesis", "Q-003")]


def test_gap_question_answered_only_by_rejected_hypothesis(drafted):
    replace(drafted / "00-charter/hypotheses.md", "status: proposed", "status: rejected")
    replace(drafted / "00-charter/hypotheses.md", 'change_reason: ""', 'change_reason: "dropped"')
    assert ("question-no-hypothesis", "Q-001") in gaps(drafted)


def test_hypothesis_from_010_template(drafted):
    append(drafted / "00-charter/hypotheses.md",
           entry("H-003", question='"Q-003"', confirm_if=None, reject_if=None,
                 change_reason=None, change_trigger=None))
    replace(drafted / "00-charter/questions.md", "hypotheses: []", 'hypotheses: ["H-003"]')
    assert check_codes(drafted) == []
    assert gaps(drafted) == [("hypothesis-no-reject", "H-003"), ("hypothesis-no-confirm", "H-003")]


def test_scope_and_people_gaps(empty):
    assert gaps(empty)[-2:] == [("no-stakeholders", None), ("no-lenses", None)]
    assert [g for g in gaps(empty) if g[0] == "scope-section-empty"] == [
        ("scope-section-empty", s) for s in
        ("Objectives", "In scope", "Out of scope", "Deliverables", "Timeline", "Constraints")]


@pytest.mark.parametrize("without_priority,fires", [(6, True), (5, False)])
def test_many_questions(empty, without_priority, fires):
    text = "".join(
        entry(f"Q-{n:03d}", priority='""' if n <= without_priority else "high") for n in range(1, 12))
    append(empty / "00-charter/questions.md", text)
    assert (("many-questions", None) in gaps(empty)) is fires


def test_gaps_do_not_affect_check(empty):
    assert gaps(empty)
    assert run_json(empty, "check")["ok"] is True
