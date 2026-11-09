"""Unit tests for the `extract-observations` helper script
(specs/005-extract-observations/contracts/observe-script.md).

Every `run()` hashes `10-sources/raw/` before and after the command and asserts nothing
changed (Principle II). Engagements are synthetic (client "Acme", code name "Northwind") and
built from the golden cases in `tests/fixtures/observe/golden/`.
"""

from __future__ import annotations

import ast
import builtins
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import OBSERVE_QUESTIONS, questions_md

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "src" / "cairn" / "assets" / "skills" / "extract-observations" / "scripts" / "observe.py"
GOLDEN = REPO / "tests" / "fixtures" / "observe" / "golden"
INGEST_US4 = REPO / "tests" / "fixtures" / "ingest" / "golden" / "us4" / "expected" / "S-001.md"
EXACT_NOT_IN_ENGAGEMENT = (
    "Not inside a Cairn engagement. Create one with `cairn init`, then run `extract-observations` "
    "from inside it."
)
# Distinctive words from the golden sources' content; `prepare` and `status` never print them.
BODY_WORDS = ("rose in both", "Prepared for the executive", "38,950", "cycle counts", "dock schedule",
              "carrier pickup windows", "Door markers")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


observe = _load("observe_script", SCRIPT)


# --- helpers ---------------------------------------------------------------------------------


def raw_hashes(eng: Path) -> dict:
    raw = eng / "10-sources" / "raw"
    return {p.relative_to(raw).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(raw.rglob("*")) if p.is_file()}


def run(eng: Path, *args, cwd=None, root=True, script=SCRIPT):
    """Run the script; return (exit code, parsed JSON). Asserts raw/ is untouched."""
    before = raw_hashes(eng)
    cmd = [sys.executable, str(script)] + (["--root", str(eng)] if root else []) + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or eng)
    assert raw_hashes(eng) == before, "10-sources/raw/ changed"
    run.stderr = result.stderr
    run.stdout = result.stdout
    try:
        return result.returncode, json.loads(result.stdout)
    except ValueError:
        return result.returncode, None


@pytest.fixture(scope="session")
def base(tmp_path_factory) -> Path:
    work = tmp_path_factory.mktemp("base")
    subprocess.run([sys.executable, "-m", "cairn", "init", "--no-git", "--engagement", "Fulfillment Review",
                    "--client", "Acme", "--code-name", "Northwind", "--lead", "Test Lead",
                    "--start-date", "2026-11-03"], cwd=work, check=True, capture_output=True)
    [eng] = [p for p in work.iterdir() if p.is_dir()]
    return eng


def set_front(path: Path, **fields) -> None:
    """Set flat front matter fields (values written as JSON scalars, or bare for bool/bare words)."""
    text = path.read_text()
    for key, value in fields.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, list):
            rendered = json.dumps(value)
        elif re.match(r"^[a-z][a-z-]*$", str(value)):
            rendered = value
        else:
            rendered = json.dumps(value)
        text, n = re.subn(rf"^{key}:.*$", lambda _: f"{key}: {rendered}", text, count=1, flags=re.M)
        assert n == 1, (path, key)
    path.write_text(text)


@pytest.fixture
def engagement(base, tmp_path):
    """Build an engagement: `cairn init` + a golden case's sources, questions and observations."""

    def make(case="us1", model_use="allowed", code_name="Northwind", questions=None) -> Path:
        eng = tmp_path / "eng"
        shutil.copytree(base, eng)
        shutil.copytree(GOLDEN / case, eng, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("expected", "drafts*.json"))
        record = eng / "engagement.md"
        set_front(record, model_use=model_use, client_code_name=code_name or "")
        if questions is not None:
            (eng / "00-charter" / "questions.md").write_text(questions_md(questions))
        raw = eng / "10-sources" / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "text-table-chart.pdf").write_bytes(b"%PDF-1.4 synthetic original, never opened\n")
        return eng

    return make


def source(eng: Path, sid: str) -> Path:
    return eng / "10-sources" / "extracted" / f"{sid}.md"


def restrict(eng: Path, sid: str, content_removed=False) -> None:
    """Mark a source restricted in its front matter and index row, then make it unreadable."""
    path = source(eng, sid)
    set_front(path, restricted=True, content_removed=content_removed)
    index = eng / "10-sources" / "index.md"
    index.write_text(re.sub(rf"^(\| {sid} \|.*\| )no \|$", r"\1yes |", index.read_text(), flags=re.M))
    os.chmod(path, 0)


@pytest.fixture(autouse=True)
def _restore_modes(tmp_path):
    yield
    for path in tmp_path.rglob("*.md"):
        try:
            os.chmod(path, 0o644)
        except OSError:
            pass


def draft(**overrides) -> dict:
    out = {
        "source": "S-001", "locator": "p. 2",
        "quote": "Order-to-ship time rose in both northern sites during Q3.",
        "claim": "The FY25 operations review says order-to-ship time rose in both northern sites during Q3.",
        "title": "Order-to-ship time rose at both northern sites in Q3",
        "questions": ["Q-003"], "confidence": "medium", "confidence_reason": "client's own review",
    }
    out.update(overrides)
    return out


TABLE_ROW = dict(locator="p. 2 › table 1 › row 2 › Days to ship", quote="| North 2 | 38,950 | 3.9 |",
                 claim="The FY25 operations review gives North 2's days to ship as 3.9.",
                 title="North 2 averages 3.9 days to ship")
CHART = dict(quote="Line chart with two lines rising between Q1 and Q3, then flattening in Q4.",
             claim="The chart description on p. 2 says the two lines flatten in Q4.",
             title="Chart lines flatten in Q4")
NEXT_STEP = dict(locator="p. 3", quote="Review carrier pickup windows with the transport team.",
                 claim="The FY25 operations review lists reviewing carrier pickup windows as a next step.",
                 title="Review asks to check carrier pickup windows")


def write_drafts(eng: Path, drafts: list, steering=None, name="drafts-test.json") -> Path:
    folder = eng / ".cairn" / "work" / "extract-observations"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    data = {"drafts": drafts}
    if steering is not False:
        data["steering"] = steering if steering is not None else {"focus": [], "exclude": [], "perspective": ""}
    path.write_text(json.dumps(data, ensure_ascii=False))
    return path


def add(eng: Path, *drafts, steering=None, flags=()):
    return run(eng, "add", write_drafts(eng, list(drafts), steering), *flags)


def refused(out: dict) -> dict:
    return {r["index"]: r["code"] for r in out["refused"]}


def inbox(eng: Path) -> list:
    return sorted(p.name for p in (eng / "_inbox").glob("O-*.md"))


def front(path: Path) -> dict:
    return observe.parse_mapping(observe.split_front_matter(path.read_text().split("\n"))[0], 2)[0]


def write_observation(eng: Path, rel: str, **fields) -> Path:
    """A copy of the us1 expected O-001 with some fields changed (and the id from the file name)."""
    path = eng / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(GOLDEN / "us1" / "expected" / "O-001.md", path)
    fields.setdefault("id", path.stem)
    set_front(path, **fields)
    return path


# --- discovery, version, arguments ---------------------------------------------------------------


def test_discovery_walks_up(engagement):
    eng = engagement()
    code, out = run(eng, "status", root=False, cwd=eng / "_inbox")
    assert code == 0 and out["engagement_name"] == "Fulfillment Review"


def test_script_path_fallback(engagement, tmp_path):
    eng = engagement()
    copy = eng / ".claude" / "skills" / "extract-observations" / "scripts" / "observe.py"
    assert copy.read_bytes() == SCRIPT.read_bytes()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    code, out = run(eng, "status", root=False, cwd=elsewhere, script=copy)
    assert code == 0 and out["client_label"] == "Northwind"


def test_not_in_engagement(engagement, tmp_path):
    eng = engagement()
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    code, out = run(eng, "status", root=False, cwd=nowhere)
    assert code == 2
    assert run.stderr.strip() == EXACT_NOT_IN_ENGAGEMENT
    assert out == {"error": "not-in-engagement", "detail": EXACT_NOT_IN_ENGAGEMENT}


def test_version():
    result = subprocess.run([sys.executable, str(SCRIPT), "--version"], capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.strip() == "observe.py 0.5.0"


@pytest.mark.parametrize("args", [["frobnicate"], ["prepare"], ["add"], ["tag", "O-001"],
                                  ["progress", "S-001"], ["progress", "S-001", "--done", "--stopped-at", "p. 1"]])
def test_bad_arguments_exit_6(engagement, args):
    eng = engagement()
    code, _ = run(eng, *args)
    assert code == 6


# --- numbering (R8) ------------------------------------------------------------------------------


def next_id(eng: Path) -> str:
    code, out = run(eng, "status")
    assert code == 0, out
    return out["next_id"]


def test_numbering_empty(engagement):
    assert next_id(engagement()) == "O-001"


def test_numbering_gaps_and_folders(engagement):
    eng = engagement()
    write_observation(eng, "_inbox/O-003.md")
    write_observation(eng, "30-observations/O-010.md", status="active")
    assert next_id(eng) == "O-011"


def test_numbering_counts_mentions_outside_observations(engagement):
    eng = engagement()
    finding = eng / "40-synthesis" / "findings" / "F-001.md"
    finding.parent.mkdir(parents=True, exist_ok=True)
    finding.write_text('---\nid: "F-001"\ntype: finding\nsupported_by: ["O-041"]\n---\n\nSee O-041.\n')
    assert next_id(eng) == "O-042"


def test_numbering_ignores_source_content_but_not_context(engagement):
    eng = engagement()
    path = source(eng, "S-001")
    path.write_text(path.read_text().replace("Next steps\n", "Next steps (see O-104)\n"))
    assert next_id(eng) == "O-001"
    path.write_text(path.read_text().replace("Their own view of FY25.", "Their own view of FY25. Cited by O-050."))
    assert next_id(eng) == "O-051"


def test_numbering_counts_rejected_and_hand_written(engagement):
    assert next_id(engagement("us4")) == "O-021"


def test_numbering_grows_to_four_digits(engagement):
    eng = engagement()
    write_observation(eng, "_inbox/O-999.md")
    assert next_id(eng) == "O-1000"
    code, out = add(eng, draft(**NEXT_STEP))
    assert code == 0 and out["written"][0]["id"] == "O-1000"
    assert (eng / "_inbox" / "O-1000.md").is_file()


# --- gates (R13) ---------------------------------------------------------------------------------


def test_unconfirmed_refuses_everything_but_verify(engagement):
    eng = engagement(model_use="unconfirmed")
    write_observation(eng, "_inbox/O-001.md")
    for args in (["status"], ["prepare", "S-001"], ["tag", "O-001", "Q-001"], ["progress", "S-001", "--done"]):
        code, out = run(eng, *args)
        assert code == 3, args
        assert out["error"] == "policy-unconfirmed"
        assert "/charter" in out["message"]
    code, out = add(eng, draft())
    assert code == 3 and out["refused"] == "policy-unconfirmed" and "Nothing was written" in out["detail"]
    assert inbox(eng) == ["O-001.md"]
    code, out = run(eng, "verify")
    assert code == 0
    assert [w["code"] for w in out["warnings"]] == ["policy-unconfirmed"]


@pytest.mark.parametrize("removed", [False, True])
def test_restricted_source_is_never_opened(engagement, removed):
    eng = engagement()
    restrict(eng, "S-004", content_removed=removed)
    code, out = run(eng, "prepare", "S-004")
    assert code == 3 and out["refused"] == "source-restricted" and out["source"] == "S-004"
    code, out = run(eng, "status")
    assert code == 0
    s4 = next(s for s in out["sources"] if s["id"] == "S-004")
    assert s4["eligible"] is False and s4["reason"] == "restricted" and s4["restricted"] is True
    assert s4["title"] == "Inbound process manual (Northwind)"


def test_restricted_source_not_opened_in_process(engagement, monkeypatch, capsys):
    """No `open` of a restricted source or of anything under raw/, for every command."""
    eng = engagement()
    restrict(eng, "S-004")
    os.chmod(source(eng, "S-004"), 0o644)  # readable, so only the code keeps it closed
    opened = []
    real_open = builtins.open

    def spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(io, "open", spy)
    drafts = write_drafts(eng, [draft(), draft(source="S-004", locator="§ Process manual",
                                               quote="This manual describes inbound receiving at the north sites.")])
    for args in (["status"], ["prepare", "S-004"], ["prepare", "S-001"], ["add", str(drafts)], ["verify"]):
        observe.main(["--root", str(eng), *args])
    capsys.readouterr()
    assert opened, "the spy saw no file opened"
    assert not [p for p in opened if p.endswith("S-004.md")], "a restricted source was opened"
    assert not [p for p in opened if "10-sources/raw" in p.replace(os.sep, "/")], "raw/ was opened"


def test_gate_exit_6_cases(engagement):
    eng = engagement()
    code, out = run(eng, "prepare", "S-099")
    assert code == 6 and out["refused"] == "source-unknown"
    set_front(source(eng, "S-002"), extraction_status="in-progress")
    code, out = run(eng, "prepare", "S-002")
    assert code == 6 and out["refused"] == "source-incomplete"
    set_front(source(eng, "S-003"), origin="llm-inference")
    code, out = run(eng, "prepare", "S-003")
    assert code == 6 and out["refused"] == "source-llm-inference"


def test_retired_source_needs_confirmed(engagement):
    eng = engagement()
    set_front(source(eng, "S-002"), status="superseded")
    set_front(source(eng, "S-004"), supersedes=["S-002"])
    code, out = run(eng, "prepare", "S-002")
    assert code == 6 and out["refused"] == "source-retired" and out["superseded_by"] == "S-004"
    code, out = run(eng, "prepare", "S-002", "--confirmed")
    assert code == 0 and out["superseded_by"] == "S-004"
    code, out = run(eng, "status")
    s2 = next(s for s in out["sources"] if s["id"] == "S-002")
    assert s2["eligible"] is False and s2["reason"] == "retired" and s2["superseded_by"] == "S-004"


# --- status and prepare -------------------------------------------------------------------------


def test_status_fields(engagement):
    eng = engagement()
    code, out = run(eng, "status")
    assert code == 0
    assert out["engagement_name"] == "Fulfillment Review" and out["client_label"] == "Northwind"
    assert out["uses_code_name"] is True and out["model_use"] == "allowed"
    assert [q["id"] for q in out["questions"]] == ["Q-001", "Q-002", "Q-003"]
    assert out["questions"][2] == {"id": "Q-003", "title": "Why is fulfilment slow", "status": "active"}
    assert [s["id"] for s in out["sources"]] == ["S-001", "S-002", "S-003", "S-004"]
    s1 = out["sources"][0]
    assert set(s1) == {"id", "title", "material", "status", "extraction_status", "restricted", "content_removed",
                       "observations", "progress", "eligible", "reason", "superseded_by"}
    assert s1["eligible"] is True and s1["reason"] == "" and s1["observations"] == 0 and s1["progress"] is None
    assert "Acme" not in run.stdout
    for word in BODY_WORDS:
        assert word not in run.stdout
    add(eng, draft(), draft(**NEXT_STEP))
    code, out = run(eng, "status", "S-001")
    assert [s["id"] for s in out["sources"]] == ["S-001"] and out["sources"][0]["observations"] == 2
    code, out = run(eng, "status", "S-077")
    assert code == 6


def test_prepare_outline(engagement):
    eng = engagement()
    code, out = run(eng, "prepare", "S-001")
    assert code == 0
    for word in BODY_WORDS:
        assert word not in run.stdout, word
    assert out["source"]["id"] == "S-001" and out["source"]["origin"] == "client-document"
    assert out["source"]["source_not_approved"] is True and out["source"]["path"] == "10-sources/extracted/S-001.md"
    assert out["cap"] == "medium"
    assert [u["locator"] for u in out["units"]] == ["p. 1", "p. 2", "p. 3"]
    assert out["tables"] == [{"unit": "p. 2", "table": 1, "rows": 2,
                              "columns": ["Site", "Orders", "Days to ship"], "line": out["tables"][0]["line"]}]
    assert [(d["unit"], d["kind"]) for d in out["derived"]] == [("p. 2", "vision-description")]
    assert out["existing"] == [] and out["progress"] is None and out["superseded_by"] == ""
    first, last = out["source"]["content_lines"]
    lines = source(eng, "S-001").read_text().split("\n")
    assert lines[first - 2] == "<!-- cairn:content:start -->" and lines[last] == "<!-- cairn:content:end -->"
    add(eng, draft())
    code, out = run(eng, "prepare", "S-001")
    assert [(e["id"], e["status"], e["folder"], e["locator"]) for e in out["existing"]] == [
        ("O-001", "proposed", "_inbox", "p. 2")]
    assert out["existing"][0]["passage"] == "Order-to-ship time rose in both northern sites during Q3."


def test_prepare_word_comments_and_tables(engagement):
    eng = engagement()
    code, out = run(eng, "prepare", "S-004")
    assert code == 0
    locators = [u["locator"] for u in out["units"]]
    assert "§ Receiving > Shifts" in locators and "comment 1 @ § Receiving" in locators
    assert [(t["unit"], t["columns"]) for t in out["tables"]] == [
        ("§ Receiving > Shifts", ["Shift", "Start", "Lead"]), ("§ Receiving > Dock wait time", ["Shift", "Minutes"])]
    assert {d["kind"] for d in out["derived"]} == {"vision-description", "chart-data", "diagram-text"}


def test_prepare_transcript_speakers_and_cap(engagement):
    eng = engagement("us3")
    code, out = run(eng, "prepare", "S-001")
    assert code == 0
    assert out["speakers"] == [{"label": "Dana", "name": "Dana Reyes"}, {"label": "Speaker 2", "name": ""},
                               {"label": "Lee", "name": ""}]
    assert out["units"][0] == {"locator": "T1", "timestamp": "00:00:04", "speaker": "Dana Reyes",
                               "line": out["units"][0]["line"]}
    assert out["units"][1]["speaker"] == "Speaker 2"
    set_front(source(eng, "S-005"), confidence="high")
    code, out = run(eng, "prepare", "S-005")
    assert out["cap"] == "medium" and out["source"]["author_kind"] == "ai-notetaker"


# --- rendering from the engagement's template (Skill Contract 4) ---------------------------------


def test_render_round_trips(engagement):
    eng = engagement()
    keys = observe.template_keys(observe.Engagement(eng))
    fields = {"id": "O-007", "type": "observation", "title": 'A "quoted" title \\ with a backslash',
              "status": "proposed", "origin": "client-document", "confidence": "medium",
              "confidence_reason": "one line", "inference_confirmed": False, "audience": "internal",
              "supports": [], "contradicts": [], "derived_from": [], "supersedes": [], "clarifies": [],
              "change_reason": "", "change_trigger": "", "created": "2026-11-06", "source": "S-001",
              "locator": "p. 2 › table 1 › row 2", "questions": ["Q-001", "Q-003"], "derived": True,
              "speaker": "", "passage_kind": "table-row", "translated": False}
    text = observe.render_observation(keys, fields, "The claim.", ["| North 2 | 38,950 | 3.9 |", "second line"])
    parsed = observe.parse_file(text, "O-007.md")
    assert parsed["problems"] == []
    got = parsed["front"]
    assert got["title"] == fields["title"] and got["questions"] == ["Q-001", "Q-003"]
    assert got["derived"] == "true" and got["passage_kind"] == "table-row" and got["locator"] == fields["locator"]
    assert list(got) == [k for k, _ in keys]
    assert "# " not in text.split("---")[1].replace("## ", "")  # no template comments
    assert text.endswith("## Claim\n\nThe claim.\n\n## Passage\n\n> | North 2 | 38,950 | 3.9 |\n> second line\n")


def test_render_follows_the_engagement_template(engagement):
    eng = engagement()
    template = eng / "_templates" / "observation.md"
    text = template.read_text()
    text = text.replace('type: observation\ntitle: ""', 'title: ""\ntype: observation')
    text = text.replace("translated: false", 'translated: false\nreviewer: ""  # who checked it (consultant field)')
    template.write_text(text)
    code, out = add(eng, draft())
    assert code == 0
    written = (eng / "_inbox" / "O-001.md").read_text()
    keys = [l.split(":")[0] for l in written.split("---")[1].strip().split("\n")]
    assert keys[:3] == ["id", "title", "type"] and keys[-1] == "reviewer"
    assert 'reviewer: ""' in written and "# who checked" not in written


@pytest.mark.parametrize("damage", ["drop-field", "missing"])
def test_outdated_template_writes_nothing(engagement, damage):
    eng = engagement()
    template = eng / "_templates" / "observation.md"
    if damage == "missing":
        template.unlink()
    else:
        template.write_text(re.sub(r"^passage_kind:.*\n", "", template.read_text(), flags=re.M))
    code, out = add(eng, draft())
    assert code == 6 and out["error"] == "template-outdated"
    assert "cairn refresh" in out["message"]
    if damage == "drop-field":
        assert out["missing"] == ["passage_kind"]
    assert inbox(eng) == []


# --- verify: structure (T019) --------------------------------------------------------------------


@pytest.mark.parametrize("fields, code", [
    ({"status": "draft"}, "bad-value"),
    ({"confidence": "very"}, "bad-value"),
    ({"passage_kind": "summary"}, "bad-value"),
    ({"title": "x" * 81}, "bad-value"),
    ({"audience": "public"}, "status-invalid"),
    ({"audience": "client-ready"}, "client-ready"),
    ({"questions": ["Q-009"]}, "question-unknown"),
    ({"locator": ""}, "missing-field"),
    ({"confidence_reason": ""}, "missing-field"),
    ({"contradicts": ["O-404"]}, "broken-link"),
    ({"source": "S-404"}, "broken-link"),
])
def test_verify_structure_codes(engagement, fields, code):
    eng = engagement()
    write_observation(eng, "_inbox/O-001.md", **fields)
    exit_code, out = run(eng, "verify")
    assert exit_code == 1
    assert {p["code"] for p in out["problems"]} == {code}, out["problems"]


def test_verify_client_ready_allowed_once_active(engagement):
    eng = engagement()
    write_observation(eng, "30-observations/O-001.md", status="active", audience="client-ready")
    code, out = run(eng, "verify")
    assert code == 0, out


def test_verify_hand_written_observation(engagement):
    eng = engagement("us4")
    code, out = run(eng, "verify", "O-020")
    assert code == 0 and out["checked"] == 1
    assert [w["code"] for w in out["warnings"]] == ["passage-missing"]
    code, out = run(eng, "verify", "O-404")
    assert code == 6


def test_script_is_python39_stdlib_only():
    text = SCRIPT.read_text()
    ast.parse(text, feature_version=(3, 9))
    tree = ast.parse(text)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert not imported & {"cairn", "ingest", "charter", "subprocess", "socket", "urllib", "http", "requests"}
    # `10-sources/raw` appears in code only as the RAW_DIR constant, used to skip that folder.
    docstring = ast.get_docstring(tree, clean=False)
    literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and "10-sources/raw" in n.value and n.value != docstring]
    assert literals == ["10-sources/raw"]


# --- US1: add --------------------------------------------------------------------------------------


@pytest.mark.parametrize("overrides, code", [
    ({"quote": ""}, "missing-field"),
    ({"claim": "  "}, "missing-field"),
    ({"confidence_reason": ""}, "missing-field"),
    ({"confidence": "very high"}, "bad-value"),
    ({"questions": "Q-001"}, "bad-value"),
    ({"translated": "yes"}, "bad-value"),
    ({"source": "doc-1"}, "bad-value"),
    ({"title": "t" * 81}, "bad-value"),
])
def test_add_required_fields(engagement, overrides, code):
    eng = engagement()
    exit_code, out = add(eng, draft(**overrides))
    assert exit_code == 0 and refused(out) == {0: code}
    assert inbox(eng) == []


@pytest.mark.parametrize("locator", ["p. 9", "§ Nowhere", "p. 2 › table 2 › row 1", "p. 2 › table 1 › row 3",
                                     "p. 2 › table 1 › row 2 › Cost", "p. 2 › row 2", "comment 4 @ § Receiving"])
def test_add_locator_unknown(engagement, locator):
    eng = engagement()
    code, out = add(eng, draft(locator=locator, quote="| North 2 | 38,950 | 3.9 |"))
    assert refused(out) == {0: "locator-unknown"}


@pytest.mark.parametrize("quote", [
    "Order-to-ship time fell in both northern sites during Q3.",
    "Order-to-ship time rose in both southern sites during Q3.",
    "In both northern sites, order-to-ship time rose during Q3.",
    "Order-to-ship time rose in both northern sites during Q3. Review carrier pickup windows",
    "Order-to-ship time rose … during Q3.",
    "Order-to-ship time rose ... during Q3.",
    "der-to-ship time rose in both",
])
def test_add_quote_not_found(engagement, quote):
    eng = engagement()
    code, out = add(eng, draft(quote=quote))
    assert refused(out) == {0: "quote-not-found"}
    if "…" in quote or "..." in quote:
        assert "no ellipses" in out["refused"][0]["detail"]


def test_add_quote_at_wrong_locator_names_the_right_one(engagement):
    eng = engagement()
    code, out = add(eng, draft(locator="p. 3"))
    assert refused(out) == {0: "quote-not-found"} and "p. 2" in out["refused"][0]["detail"]


@pytest.mark.parametrize("overrides", [
    {"quote": "Order-to-ship   time rose\nin both northern\n  sites during Q3."},
    {"quote": "Order-to-ship time rose in both northern sites during Q3"},
    {"quote": "> **Description:** Line chart with two lines rising between Q1 and Q3",
     "claim": "The chart description on p. 2 says the two lines rise from Q1 to Q3.", "title": "Chart lines rise"},
    {"locator": "p. 2 › table 1 › row 2", "quote": "|North 2|38,950 |  3.9|", "claim": "North 2 row.",
     "title": "North 2 row"},
    {"locator": "p. 2 › table 1 › row 2 › Orders", "quote": "38,950", "claim": "North 2 had 38,950 orders.",
     "title": "North 2 orders"},
])
def test_add_normalisation_still_matches(engagement, overrides):
    eng = engagement()
    code, out = add(eng, draft(**overrides))
    assert code == 0 and out["refused"] == [], out


def test_add_quote_across_callout_line_break(engagement):
    eng = engagement()
    code, out = add(eng, draft(source="S-002", quote="NOTE: Q4 FIGURES ARE PROVISIONAL AND MAY BE REVISED.",
                               claim="The scanned appendix notes that Q4 figures are provisional and may be revised.",
                               title="Q4 figures are provisional", confidence="low",
                               confidence_reason="OCR of a scanned page"))
    assert out["refused"] == [], out
    written = out["written"][0]
    assert written["derived"] is True
    fields = front(eng / "_inbox" / "O-001.md")
    assert fields["confidence_reason"] == "uncertain extraction: OCR of a scanned page"


def test_add_corrected_callouts(engagement):
    eng = engagement()
    text = INGEST_US4.read_text().replace('id: "S-001"', 'id: "S-005"', 1)
    source(eng, "S-005").write_text(text)
    low = dict(source="S-005", locator="p. 1", confidence="low", confidence_reason="OCR, fixed in review")
    code, out = add(eng,
                    draft(quote="FIGURES ARE TAKEN FROM THE WMS SHIPMENT LOG, EXCLUDING RETURNS.",
                          claim="The appendix says figures are taken from the WMS shipment log, excluding returns.",
                          title="Figures come from the WMS shipment log", **low),
                    draft(quote="FIGURES ARE TAKEN FROM THE VMS", claim="Old text.", title="Old", **low))
    assert refused(out) == {1: "quote-not-found"}
    assert out["written"][0]["derived"] is True


@pytest.mark.parametrize("sid, locator, quote", [
    ("S-001", "p. 2", "Sent by the COO's office on 2026-10-14 ahead of the kickoff."),
    ("S-001", "p. 2", "A 3-page internal operations review with a site table"),
    ("S-001", "p. 1", "| Label | Confirmed name |"),
    ("S-003", "p. 2", "text too faint to read reliably"),
])
def test_add_quote_outside_content(engagement, sid, locator, quote):
    eng = engagement()
    code, out = add(eng, draft(source=sid, locator=locator, quote=quote, confidence="low"))
    assert refused(out) == {0: "quote-outside-content"}


def test_add_quote_too_short_except_table_rows(engagement):
    eng = engagement()
    code, out = add(eng, draft(quote="during Q3."),
                    draft(locator="p. 2 › table 1 › row 2", quote="North 2", claim="Row two is North 2.",
                          title="Row two is North 2"))
    assert refused(out) == {0: "quote-too-short"}
    assert [w["passage_kind"] for w in out["written"]] == ["table-row"]


def test_add_table_locator_missing(engagement):
    eng = engagement()
    code, out = add(eng, draft(quote="| North 2 | 38,950 | 3.9 |"))
    assert refused(out) == {0: "table-locator-missing"}
    assert "p. 2 › table 1 › row 2" in out["refused"][0]["detail"]


def test_add_confidence_caps(engagement):
    eng = engagement()
    uncertain = dict(source="S-003", quote="Footnote: cycle counts were skipped on two Fridays in September.",
                     claim="The checklist says cycle counts were skipped on two Fridays in September.",
                     title="Cycle counts skipped on two Fridays")
    code, out = add(eng, draft(confidence="high"),
                    draft(confidence="medium", **uncertain),
                    draft(confidence="low", confidence_reason="faint page", **uncertain))
    assert refused(out) == {0: "confidence-cap", 1: "confidence-cap"}
    assert "uncertain" in out["refused"][1]["detail"]
    assert front(eng / "_inbox" / "O-001.md")["confidence_reason"] == "uncertain extraction: faint page"


def test_add_question_unknown(engagement):
    eng = engagement()
    code, out = add(eng, draft(questions=["Q-009"]))
    assert refused(out) == {0: "question-unknown"}


def test_add_duplicate_in_both_folders(engagement):
    eng = engagement()
    code, out = add(eng, draft(), draft())
    assert refused(out) == {1: "duplicate"}
    code, out = add(eng, draft(claim="The FY25 operations review says ORDER-to-ship time rose in both northern "
                                     "sites during Q3"))
    assert refused(out) == {0: "duplicate"}
    shutil.move(str(eng / "_inbox" / "O-001.md"), str(eng / "30-observations" / "O-001.md"))
    set_front(eng / "30-observations" / "O-001.md", status="active")
    code, out = add(eng, draft())
    assert refused(out) == {0: "duplicate"} and "O-001" in out["refused"][0]["detail"]


def test_add_real_name_leak(engagement):
    eng = engagement()
    path = source(eng, "S-001")
    path.write_text(path.read_text().replace("Prepared for the executive team\n",
                                             "Prepared for the executive team\nAcme internal use only, all sites.\n"))
    passage = dict(locator="p. 1", quote="Acme internal use only, all sites.")
    code, out = add(eng, draft(title="Acme order-to-ship rose in Q3"),
                    draft(claim="The review says ACME's order-to-ship time rose."),
                    draft(claim="The review is marked for Northwind internal use only, at all sites.",
                          title="Review is for internal use only", questions=[], **passage),
                    draft(title="Acmecorp style is fine"))
    assert refused(out) == {0: "real-name-leak", 1: "real-name-leak"}
    assert [w["title"] for w in out["written"]][1] == "[redacted]corp style is fine"  # whole words only
    assert "Acme" not in run.stdout and "ACME" not in run.stdout
    assert "> Acme internal use only" in (eng / "_inbox" / "O-001.md").read_text()


def test_add_computed_fields(engagement):
    eng = engagement()
    code, out = add(eng, draft(), draft(**CHART), draft(**TABLE_ROW))
    assert out["refused"] == []
    first, chart, row = (front(eng / "_inbox" / f"O-00{n}.md") for n in (1, 2, 3))
    assert first["origin"] == "client-document" and first["derived"] == "false" and first["passage_kind"] == "text"
    assert chart["derived"] == "true" and chart["passage_kind"] == "text"
    assert row["derived"] == "false" and row["passage_kind"] == "table-row"
    assert first["status"] == "proposed" and first["audience"] == "internal" and first["speaker"] == ""
    assert first["inference_confirmed"] == "false" and first["supports"] == []


def test_add_order_dry_run_and_shape(engagement):
    eng = engagement()
    code, out = add(eng, draft(), draft(quote="nonsense words here"), draft(**NEXT_STEP), flags=["--dry-run"])
    assert code == 0 and inbox(eng) == [] and out["dry_run"] is True
    assert [w["id"] for w in out["written"]] == ["O-001", "O-002"] and out["next_id"] == "O-003"
    code, out = add(eng, draft(), draft(quote="nonsense words here"), draft(**NEXT_STEP))
    assert set(out) >= {"written", "refused", "warnings", "next_id"}
    assert [(w["id"], w["locator"]) for w in out["written"]] == [("O-001", "p. 2"), ("O-002", "p. 3")]
    assert set(out["written"][0]) >= {"id", "title", "source", "locator", "questions", "derived", "confidence"}
    assert out["refused"] == [{"index": 1, "code": "quote-not-found", "detail": out["refused"][0]["detail"]}]
    assert inbox(eng) == ["O-001.md", "O-002.md"] and out["next_id"] == "O-003"
    assert out["sources_not_approved"] == ["S-001"]


def test_add_interrupted_leaves_valid_prefix(engagement, monkeypatch, capsys):
    eng = engagement()
    path = write_drafts(eng, [draft(), draft(**NEXT_STEP), draft(**CHART)])
    real = observe.atomic_write
    calls = []

    def flaky(target, text):
        calls.append(target)
        if len(calls) == 3:
            raise KeyboardInterrupt
        real(target, text)

    monkeypatch.setattr(observe, "atomic_write", flaky)
    with pytest.raises(KeyboardInterrupt):
        observe.main(["--root", str(eng), "add", str(path)])
    capsys.readouterr()
    assert inbox(eng) == ["O-001.md", "O-002.md"]
    assert not [p for p in (eng / "_inbox").iterdir() if p.name.startswith(".O-")]
    code, out = run(eng, "verify")
    assert code == 0, out


@pytest.mark.parametrize("removed", [False, True])
def test_add_policy_gate_aborts_whole_run(engagement, removed):
    eng = engagement()
    restrict(eng, "S-004", content_removed=removed)
    code, out = add(eng, draft(), draft(source="S-004", locator="§ Process manual",
                                        quote="This manual describes inbound receiving at the north sites."),
                    draft(**NEXT_STEP))
    assert code == 3
    assert out == {"refused": "source-restricted", "source": "S-004", "detail": "Nothing was written."}
    assert inbox(eng) == []


def test_add_per_draft_gates(engagement):
    eng = engagement()
    set_front(source(eng, "S-002"), extraction_status="in-progress")
    set_front(source(eng, "S-003"), origin="llm-inference")
    set_front(source(eng, "S-004"), status="superseded")
    word = dict(source="S-004", locator="§ Process manual",
                quote="This manual describes inbound receiving at the north sites.",
                claim="The process manual says it describes inbound receiving at the north sites.",
                title="Manual covers inbound receiving")
    drafts = [draft(source="S-099"), draft(source="S-002"), draft(source="S-003"), draft(**word), draft()]
    code, out = add(eng, *drafts)
    assert code == 0
    assert refused(out) == {0: "source-unknown", 1: "source-incomplete", 2: "source-llm-inference",
                            3: "source-retired"}
    assert [w["source"] for w in out["written"]] == ["S-001"]
    code, out = add(eng, draft(**word), flags=["--confirmed"])
    assert [w["source"] for w in out["written"]] == ["S-004"]


def test_add_unreadable_drafts(engagement):
    eng = engagement()
    path = eng / ".cairn" / "work" / "extract-observations" / "bad.json"
    path.parent.mkdir(parents=True)
    for content in ("not json", "[]", '{"drafts": [1]}', '{"drafts": [], "steering": {"focus": "Q-001"}}'):
        path.write_text(content)
        code, out = run(eng, "add", path)
        assert code == 6 and out["error"] == "drafts-unreadable", content
    code, out = run(eng, "add", eng / "missing.json")
    assert code == 6


# --- US2: steering ----------------------------------------------------------------------------------


def focus(*ids, exclude=(), perspective=""):
    return {"focus": list(ids), "exclude": list(exclude), "perspective": perspective}


S005 = dict(source="S-005", confidence="medium", confidence_reason="client's draft review")


def test_unknown_focus_refuses_the_file(engagement):
    eng = engagement("us2")
    code, out = add(eng, draft(), steering=focus("Q-009"))
    assert code == 6 and out["error"] == "question-unknown" and out["ids"] == ["Q-009"]
    assert inbox(eng) == []


def test_off_focus_and_untagged(engagement):
    eng = engagement("us2")
    code, out = add(eng, draft(questions=["Q-001"]), draft(**NEXT_STEP, questions=[]),
                    draft(questions=["Q-001", "Q-003"]), steering=focus("Q-003"))
    assert refused(out) == {0: "off-focus", 1: "off-focus"}
    assert len(out["written"]) == 1
    code, out = add(eng, draft(**NEXT_STEP, questions=[]))
    assert out["refused"] == [] and out["written"][0]["questions"] == []


@pytest.mark.parametrize("entry, locator, quote, excluded", [
    ("§ Appendix", "§ Appendix > Detail", "Carrier pickup times were taken from the transport team's schedule.", True),
    ("§ Appendix", "§ Appendices", "A list of the appendices follows the detail tables.", False),
    ("§ Fulfilment review > Findings", "§ Fulfilment review > Findings",
     "Orders released after 3 pm miss the same-day carrier pickup.", True),
    ("§ Fulfilment review > Findings", "§ Fulfilment review", "Draft for the north sites, October 2026.", False),
])
def test_exclusion_by_heading(engagement, entry, locator, quote, excluded):
    eng = engagement("us2")
    code, out = add(eng, draft(locator=locator, quote=quote, **S005), steering=focus(exclude=[entry]))
    assert refused(out) == ({0: "excluded"} if excluded else {}), out


@pytest.mark.parametrize("entry, excluded", [("p. 2–3", True), ("p. 2-3", True), ("p. 3–9", False),
                                             ("p. 2", True), ("p. 1", False), ("p. 2 › table 1", False)])
def test_exclusion_by_page(engagement, entry, excluded):
    eng = engagement("us2")
    code, out = add(eng, draft(), steering=focus(exclude=[entry]))
    assert refused(out) == ({0: "excluded"} if excluded else {}), out


@pytest.mark.parametrize("entry, excluded", [("speaker: Speaker 2", True), ("speaker: speaker 2", True),
                                             ("speaker: Dana Reyes", False), ("speaker: Dana", False)])
def test_exclusion_by_speaker(engagement, entry, excluded):
    eng = engagement("us3")
    code, out = add(eng, draft(source="S-006", locator="T2",
                               quote="Honestly, sales always sends the orders late, that's the whole problem.",
                               claim="Speaker 2 said sales always sends the orders late.",
                               title="Speaker 2 says sales sends orders late"),
                    steering=focus(exclude=[entry]))
    assert refused(out) == ({0: "excluded"} if excluded else {}), out
    eng2 = eng.parent / "eng2"
    shutil.copytree(eng, eng2)
    shutil.rmtree(eng2 / "_inbox")
    (eng2 / "_inbox").mkdir()
    code, out = add(eng2, draft(source="S-006", locator="T4",
                                quote="We estimated that about a third of orders arrive after the cut-off.",
                                claim="Dana Reyes said they estimated a third of orders arrive after the cut-off.",
                                title="Dana estimates a third of orders arrive late"),
                    steering=focus(exclude=["speaker: Dana Reyes"]))
    assert refused(out) == {0: "excluded"}


def test_question_retired_warning(engagement):
    questions = [dict(q) for q in OBSERVE_QUESTIONS]
    questions[1]["status"] = "superseded"
    eng = engagement(questions=questions)
    code, out = add(eng, draft(questions=["Q-002"]),
                    draft(**NEXT_STEP, questions=["Q-002"], accept_warnings=["question-retired"]))
    assert refused(out) == {0: "question-retired"}
    assert [(w["index"], w["code"]) for w in out["warnings"]] == [(1, "question-retired")]


def test_steering_defaults_and_no_questions(engagement):
    eng = engagement(questions=[])
    code, out = run(eng, "status")
    assert out["questions"] == []
    path = write_drafts(eng, [draft(questions=[])], steering={"exclude": []})
    code, out = run(eng, "add", path)
    assert code == 0 and out["steering"] == focus() and len(out["written"]) == 1
    path = write_drafts(eng, [draft(**NEXT_STEP, questions=[])], steering=False)
    code, out = run(eng, "add", path)
    assert code == 0 and len(out["written"]) == 1


def test_two_sources_in_one_file(engagement):
    eng = engagement("us2")
    code, out = add(eng, draft(), draft(locator="§ Fulfilment review > Findings",
                                        quote="Orders released after 3 pm miss the same-day carrier pickup.",
                                        claim="The draft review says orders released after 3 pm miss the pickup.",
                                        title="Late releases miss the pickup", **S005), steering=focus("Q-003"))
    assert [w["source"] for w in out["written"]] == ["S-001", "S-005"]


# --- US3: meetings, notes, comments, tracked changes --------------------------------------------------


def test_speaker_from_speakers_table(engagement):
    eng = engagement("us3")
    code, out = add(eng,
                    draft(source="S-006", locator="T4",
                          quote="We estimated that about a third of orders arrive after the cut-off.",
                          claim="Dana Reyes said they estimated that about a third of orders arrive after the cut-off.",
                          title="Dana Reyes estimates a third of orders arrive late"),
                    draft(source="S-001", locator="00:00:11",
                          quote="The backlog really started in July, when we lost two shift leads.",
                          claim="Speaker 2 said the backlog really started in July.", title="Backlog started in July"),
                    draft(source="S-001", locator="T4", quote="Earlier, by about an hour, for both carriers.",
                          claim="Speaker 2 said the pickup windows moved earlier by about an hour.",
                          title="Pickup windows moved earlier by an hour"))
    assert out["refused"] == [], out
    assert [w["speaker"] for w in out["written"]] == ["Dana Reyes", "Speaker 2", "Speaker 2"]


def test_attribution_missing(engagement):
    eng = engagement("us3")
    opinion = dict(source="S-006", locator="T2",
                   quote="Honestly, sales always sends the orders late, that's the whole problem.",
                   claim="Sales always sends the orders late.", title="Sales sends orders late")
    code, out = add(eng, draft(**opinion), draft(**opinion, accept_warnings=["attribution-missing"]))
    assert refused(out) == {0: "attribution-missing"}
    assert [(w["index"], w["code"]) for w in out["warnings"]] == [(1, "attribution-missing")]


def test_summary_attribution_missing(engagement):
    eng = engagement("us3")
    note = dict(source="S-003", locator="§ Weekly sync, north sites > Discussion",
                quote="The backlog at North 2 is down from last week.")
    code, out = add(eng, draft(claim="The backlog at North 2 is down from last week.", **note),
                    draft(claim="Sam Okafor's write-up says the backlog at North 2 is down.", title="a", **note),
                    draft(claim="The weekly notes say the North 2 backlog is down from last week.", title="b",
                          **{**note, "quote": "The backlog at North 2 is down from last week."}))
    assert refused(out) == {0: "summary-attribution-missing", 2: "same-passage"}


def test_ai_notes_capped_at_medium(engagement):
    eng = engagement("us3")
    set_front(source(eng, "S-005"), confidence="high")
    ai = dict(source="S-005", locator="§ Weekly sync, AI notes > Summary",
              quote="Team agreed to pilot a second shift at North 2 starting in January.",
              claim="The AI notes by MeetBot report that the team agreed to pilot a second shift at North 2.",
              title="AI notes report a second-shift pilot")
    code, out = add(eng, draft(confidence="high", **ai), draft(**ai))
    assert refused(out) == {0: "confidence-cap"} and "AI note-taker" in out["refused"][0]["detail"]


def test_comment_and_tracked_change(engagement):
    eng = engagement("us3")
    comment = dict(source="S-004", locator="comment 1 @ § Receiving", confidence="low",
                   quote="Is this still true since the new dock schedule?")
    change = dict(source="S-004", locator="§ Receiving", confidence="low",
                  quote="Pallets are checked against the ASN {++within two hours ++}on arrival{-- at the dock--}.")
    code, out = add(eng,
                    draft(claim="Someone asks whether this is still true.", title="c1", **comment),
                    draft(claim="A reviewer comment by J. Ortiz asks whether this is still true.", title="c2", **comment),
                    draft(claim="Pallets are checked within two hours on arrival.", title="t1", **change),
                    draft(claim="An unaccepted tracked change would make the text say pallets are checked within "
                                "two hours.", title="t2", **change),
                    draft(claim="A comment asks this.", title="c3", **{**comment, "locator": "comment 1 @ § Shifts"}))
    assert refused(out) == {0: "kind-unstated", 2: "kind-unstated", 4: "locator-unknown"}
    assert [(w["id"], w["passage_kind"]) for w in out["written"]] == [("O-001", "comment"), ("O-002", "tracked-change")]


def test_translated_claim(engagement):
    eng = engagement()
    code, out = add(eng, draft(translated=True),
                    draft(**{**NEXT_STEP, "translated": True, "claim": NEXT_STEP["claim"][:-1] + " (translated)."}))
    assert refused(out) == {0: "bad-value"}
    assert front(eng / "_inbox" / "O-001.md")["translated"] == "true"


def test_verify_recomputes_speaker_and_kind(engagement):
    eng = engagement("us3")
    for name in ("O-002.md", "O-007.md"):
        shutil.copy(GOLDEN / "us3" / "expected" / name, eng / "_inbox" / name)
    assert run(eng, "verify")[0] == 0
    set_front(eng / "_inbox" / "O-002.md", speaker="Lee")
    set_front(eng / "_inbox" / "O-007.md", passage_kind="text")
    code, out = run(eng, "verify")
    assert code == 1
    assert sorted((p["id"], p["code"]) for p in out["problems"]) == [("O-002", "bad-value"), ("O-007", "bad-value")]


# --- US4: re-runs, tags, progress -----------------------------------------------------------------------


def test_previously_rejected_and_superseded(engagement):
    eng = engagement()
    add(eng, draft(), draft(**NEXT_STEP))
    set_front(eng / "_inbox" / "O-001.md", status="rejected", change_reason="not useful", change_trigger="rethinking")
    set_front(eng / "_inbox" / "O-002.md", status="superseded")
    code, out = add(eng, draft(), draft(**NEXT_STEP))
    assert refused(out) == {0: "previously-rejected", 1: "duplicate"}


def test_same_passage_warning(engagement):
    eng = engagement()
    add(eng, draft())
    other = dict(claim="The FY25 operations review places the order-to-ship rise in Q3.", title="Rise was in Q3")
    shorter = dict(quote="rose in both northern sites during Q3.", claim="Both northern sites saw a rise.",
                   title="Both northern sites rose")
    code, out = add(eng, draft(**other), draft(**shorter), draft(**other, accept_warnings=["same-passage"]))
    assert refused(out) == {0: "same-passage", 1: "same-passage"}
    assert out["refused"][0]["existing"] == "O-001"
    assert [(w["index"], w["code"], w["existing"]) for w in out["warnings"]] == [(2, "same-passage", "O-001")]
    assert out["written"][0]["id"] == "O-002"


def test_tag_adds_questions_and_logs(engagement):
    eng = engagement("us4")
    target = eng / "_inbox" / "O-004.md"
    before = target.read_text()
    log = eng / "60-log" / "changelog.md"
    assert log.read_text().rstrip().endswith("No changes yet.")
    code, out = run(eng, "tag", "O-004", "Q-004", "Q-002", "Q-001")
    assert code == 0 and out == {"tagged": [{"id": "O-004", "added": ["Q-004", "Q-001"]}], "unchanged": []}
    after = target.read_text()
    assert after == before.replace('questions: ["Q-002"]', 'questions: ["Q-002", "Q-004", "Q-001"]')
    text = log.read_text()
    assert "No changes yet." not in text
    assert re.search(r"^\d{4}-\d{2}-\d{2} · O-004 · tag · added Q-004, Q-001 · -$", text, re.M)
    code, out = run(eng, "tag", "O-001", "Q-004")
    assert code == 0 and out["tagged"][0]["id"] == "O-001"
    assert 'questions: ["Q-003", "Q-004"]' in (eng / "30-observations" / "O-001.md").read_text()
    assert len(re.findall(r" · tag · ", log.read_text())) == 2
    code, out = run(eng, "tag", "O-004", "Q-004")
    assert code == 0 and out == {"tagged": [], "unchanged": ["O-004"]}
    assert len(re.findall(r" · tag · ", log.read_text())) == 2


def test_tag_keeps_other_bytes(engagement):
    eng = engagement("us4")
    target = eng / "30-observations" / "O-020.md"
    data = target.read_bytes().replace(b"\n", b"\r\n").replace(b'questions: ["Q-003"]', b'questions: ["Q-003"]   # mine')
    target.write_bytes(data)
    code, out = run(eng, "tag", "O-020", "Q-001")
    assert code == 0
    assert target.read_bytes() == data.replace(b'questions: ["Q-003"]   # mine', b'questions: ["Q-003", "Q-001"]   # mine')


@pytest.mark.parametrize("args", [["O-099", "Q-001"], ["O-004", "Q-009"], ["O-004", "Q-001", "Q-009"]])
def test_tag_refuses_unknown_ids(engagement, args):
    eng = engagement("us4")
    before = {p.name: p.read_bytes() for p in (eng / "_inbox").glob("*.md")}
    log = (eng / "60-log" / "changelog.md").read_bytes()
    code, out = run(eng, "tag", *args)
    assert code == 6
    assert {p.name: p.read_bytes() for p in (eng / "_inbox").glob("*.md")} == before
    assert (eng / "60-log" / "changelog.md").read_bytes() == log


def test_progress_round_trip(engagement):
    eng = engagement()
    drafts = write_drafts(eng, [], steering=focus("Q-003", exclude=["p. 3"]))
    code, out = run(eng, "progress", "S-001", "--stopped-at", "p. 2", "--steering-from", drafts)
    assert code == 0
    entry = out["progress"]["S-001"]
    assert entry["state"] == "stopped" and entry["stopped_at"] == "p. 2"
    assert entry["steering"] == focus("Q-003", exclude=["p. 3"]) and re.match(r"^\d{4}-\d{2}-\d{2}$", entry["updated"])
    stored = json.loads((eng / ".cairn" / "work" / "extract-observations" / "progress.json").read_text())
    assert stored == {"S-001": entry}
    assert run(eng, "prepare", "S-001")[1]["progress"] == entry
    assert run(eng, "status", "S-001")[1]["sources"][0]["progress"] == entry
    code, out = run(eng, "progress", "S-003", "--done")
    assert out["progress"]["S-003"]["state"] == "done"
    stored = json.loads((eng / ".cairn" / "work" / "extract-observations" / "progress.json").read_text())
    assert set(stored) == {"S-001", "S-003"}
    code, out = run(eng, "progress", "S-001", "--stopped-at", "p. 7")
    assert code == 6 and out["error"] == "locator-unknown"


def test_lost_progress_changes_nothing_else(engagement):
    eng = engagement()
    add(eng, draft())
    run(eng, "progress", "S-001", "--stopped-at", "p. 2")
    (eng / ".cairn" / "work" / "extract-observations" / "progress.json").unlink()
    code, out = run(eng, "prepare", "S-001")
    assert code == 0 and out["progress"] is None and [e["id"] for e in out["existing"]] == ["O-001"]
    code, out = add(eng, draft())
    assert refused(out) == {0: "duplicate"}
