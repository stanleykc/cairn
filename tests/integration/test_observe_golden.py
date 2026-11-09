"""Golden synthetic engagements for `extract-observations` (005): `add` on hand-checked drafts
writes exactly the expected observations, `verify` passes on them, and `verify` reports the
right code for each kind of broken observation (SC-001, SC-002, SC-003, SC-007, SC-008)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "src" / "cairn" / "assets" / "skills" / "extract-observations" / "scripts" / "observe.py"
INGEST_SCRIPT = REPO / "src" / "cairn" / "assets" / "skills" / "ingest" / "scripts" / "ingest.py"
GOLDEN = REPO / "tests" / "fixtures" / "observe" / "golden"
INGEST_GOLDEN = REPO / "tests" / "fixtures" / "ingest" / "golden"
CASES = sorted(p.name for p in GOLDEN.iterdir() if p.is_dir())
# Golden sources copied byte for byte from the ingest golden expectations (never re-extracted).
COPIED = {
    "us1": {"S-001": "us1", "S-002": "us1", "S-003": "us1", "S-004": "us1"},
    "us2": {"S-001": "us1", "S-002": "us1", "S-003": "us1", "S-004": "us1"},
    "us3": {"S-001": "us2", "S-002": "us2", "S-003": "us2", "S-004": "us1"},
    "us4": {"S-001": "us1", "S-002": "us1", "S-003": "us1", "S-004": "us1"},
}


def run(eng: Path, *args, script=SCRIPT) -> tuple:
    result = subprocess.run([sys.executable, str(script), "--root", str(eng), *args],
                            capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout)


def golden_engagement(tmp_path: Path, case: str) -> Path:
    record = yaml.safe_load((GOLDEN / case / "engagement.md").read_text().split("---\n")[1])
    work = tmp_path / "work"
    work.mkdir()
    args = ["init", "--no-git", "--engagement", record["engagement_name"], "--client", record["client"],
            "--lead", record["lead_consultant"], "--start-date", "2026-11-03"]
    if record.get("client_code_name"):
        args += ["--code-name", record["client_code_name"]]
    subprocess.run([sys.executable, "-m", "cairn", *args], cwd=work, check=True, capture_output=True)
    [eng] = [p for p in work.iterdir() if p.is_dir()]
    shutil.copytree(GOLDEN / case, eng, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("expected", "drafts*.json"))
    raw = eng / "10-sources" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "planted.txt").write_text("An original that must never be opened or changed.\n")
    return eng


def raw_hashes(eng: Path) -> dict:
    raw = eng / "10-sources" / "raw"
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.rglob("*")) if p.is_file()}


def normalized(text: str) -> str:
    return re.sub(r'^created: ".*"$', 'created: "<today>"', text, flags=re.M)


def front(text: str) -> dict:
    return yaml.safe_load(text.split("---\n")[1])


def add_and_compare(eng: Path, case: str, drafts: str) -> dict:
    before = raw_hashes(eng)
    code, out = run(eng, "add", str(GOLDEN / case / drafts))
    assert code == 0, out
    assert raw_hashes(eng) == before
    expected = sorted((GOLDEN / case / "expected").glob("O-*.md"))
    assert [w["id"] for w in out["written"]] == [p.stem for p in expected]
    for path in expected:
        written = (eng / "_inbox" / path.name).read_text()
        assert normalized(written) == normalized(path.read_text()), path.name
    return out


# --- every case's sources are valid ingest output -----------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_golden_sources_pass_ingest_verify(tmp_path, case):
    """Hand-built source rule: ingest's own verify reports no problems on every golden source."""
    eng = golden_engagement(tmp_path, case)
    code, out = run(eng, "verify", script=INGEST_SCRIPT)
    assert out["problems"] == [], out["problems"]
    assert {w["code"] for w in out["warnings"]} <= {"original-missing", "fidelity-unchecked"}
    assert code == 0


@pytest.mark.parametrize("case", sorted(COPIED))
def test_copied_sources_match_ingest_expectations(case):
    for id_, ingest_case in COPIED[case].items():
        ours = GOLDEN / case / "10-sources" / "extracted" / f"{id_}.md"
        theirs = INGEST_GOLDEN / ingest_case / "expected" / f"{id_}.md"
        assert ours.read_bytes() == theirs.read_bytes(), f"{case}/{id_} drifted from ingest {ingest_case}"


# --- US1 ------------------------------------------------------------------------------------------


def test_us1_add_writes_expected_and_verify_passes(tmp_path):
    eng = golden_engagement(tmp_path, "us1")
    out = add_and_compare(eng, "us1", "drafts.json")
    assert out["refused"] == [] and out["warnings"] == []
    for path in (eng / "_inbox").glob("O-*.md"):
        fields = front(path.read_text())
        assert fields["status"] == "proposed" and fields["audience"] == "internal"
        assert all(fields[k] == [] for k in ("supports", "contradicts", "derived_from", "supersedes", "clarifies"))
    code, report = run(eng, "verify")
    assert code == 0, report
    assert report["problems"] == []


# (file, regex old, new, expected code)
BROKEN = [
    ("O-001.md", r"^> Order-to-ship time rose", "> Order-to-ship time fell", "quote-not-found"),
    ("O-002.md", r"› row 2 › Days", "› row 1 › Days", "quote-not-found"),
    ("O-001.md", r"^audience: internal$", "audience: client-ready", "client-ready"),
    ("O-008.md", r"^confidence: low$", "confidence: high", "confidence-cap"),
    ("O-001.md", r'^source: "S-001"$', 'source: ""', "missing-field"),
    ("O-001.md", r"^supports: \[\]$", 'supports: ["F-001"]', "broken-link"),
    ("O-001.md", r"^origin: client-document$", "origin: llm-inference", "bad-value"),
    ("O-003.md", r"^derived: true$", "derived: false", "derived-flag"),
    ("O-002.md", r" › table 1 › row 2 › Days to ship", "", "table-locator-missing"),
    ("O-001.md", r"^title: .*$", 'title: "Acme says order-to-ship rose"', "real-name-leak"),
]


@pytest.mark.parametrize("name, old, new, code", BROKEN, ids=[b[3] + ":" + b[0] for b in BROKEN])
def test_us1_verify_reports_broken_observation(tmp_path, name, old, new, code):
    eng = golden_engagement(tmp_path, "us1")
    inbox = eng / "_inbox"
    for path in (GOLDEN / "us1" / "expected").glob("O-*.md"):
        shutil.copy(path, inbox / path.name)
    target = inbox / name
    text, n = re.subn(old, new, target.read_text(), count=1, flags=re.M)
    assert n == 1, (name, old)
    target.write_text(text)
    exit_code, report = run(eng, "verify")
    assert exit_code == 1
    codes = {p["code"] for p in report["problems"]}
    assert codes == {code}, report["problems"]
    assert {p["id"] for p in report["problems"]} == {name[:-3]}


# --- US2 ------------------------------------------------------------------------------------------


def test_us2_steering(tmp_path):
    eng = golden_engagement(tmp_path, "us2")
    out = add_and_compare(eng, "us2", "drafts-focus.json")
    assert [(r["index"], r["code"]) for r in out["refused"]] == [
        (1, "off-focus"), (2, "excluded"), (3, "excluded"), (4, "off-focus")]
    for path in (eng / "_inbox").glob("O-*.md"):
        fields = front(path.read_text())
        assert "Q-003" in fields["questions"]
        assert not fields["locator"].startswith("§ Appendix") and fields["locator"] != "p. 3"  # SC-003
    code, report = run(eng, "verify")
    assert code == 0, report


# --- US3 ------------------------------------------------------------------------------------------


def test_us3_attribution(tmp_path):
    eng = golden_engagement(tmp_path, "us3")
    out = add_and_compare(eng, "us3", "drafts.json")
    assert out["refused"] == [] and out["warnings"] == []
    transcripts = {"S-001", "S-002", "S-006"}
    for path in (eng / "_inbox").glob("O-*.md"):
        fields = front(path.read_text())
        if fields["source"] in transcripts:
            assert fields["speaker"], path.name
            assert re.match(r"^(\d{2}:\d{2}:\d{2}|T\d+)$", fields["locator"]), fields["locator"]
        if fields["source"] == "S-005":
            assert fields["confidence"] != "high"
    kinds = {front(p.read_text())["passage_kind"] for p in (eng / "_inbox").glob("O-*.md")}
    assert {"comment", "tracked-change", "text"} <= kinds
    code, report = run(eng, "verify")
    assert code == 0, report


# --- US4 ------------------------------------------------------------------------------------------


def test_us4_rerun(tmp_path):
    eng = golden_engagement(tmp_path, "us4")
    before = {p.name: p.read_bytes() for p in (eng / "_inbox").glob("O-*.md")}
    out = add_and_compare(eng, "us4", "drafts-rerun.json")
    codes = {r["index"]: r["code"] for r in out["refused"]}
    assert codes[1] == "previously-rejected"
    assert all(codes[i] == "duplicate" for i in (0, 2, 3, 4, 5, 6, 7))
    assert codes[9] == "same-passage"
    assert [r for r in out["refused"] if r["index"] == 9][0]["existing"] == "O-001"
    assert [w["id"] for w in out["written"]] == ["O-021"] and out["next_id"] == "O-022"
    for name, data in before.items():
        assert (eng / "_inbox" / name).read_bytes() == data, name
    code, report = run(eng, "verify")
    assert code == 0, report
    assert [w["code"] for w in report["warnings"]] == ["passage-missing"]
    assert report["warnings"][0]["id"] == "O-020"


# --- Constitution review gate (T063) ---------------------------------------------------------------


@pytest.mark.parametrize("case", ["us1", "us2", "us3", "us4"])
def test_expected_observations_are_proposed_cited_and_unlinked(case):
    for path in (GOLDEN / case / "expected").glob("O-*.md"):
        text = path.read_text()
        fields = front(text)
        assert fields["status"] == "proposed" and fields["audience"] == "internal"
        assert re.match(r"^S-\d{3}$", fields["source"]) and fields["locator"]
        assert fields["origin"] != "llm-inference" and fields["confidence_reason"]
        assert all(fields[k] == [] for k in ("supports", "contradicts", "derived_from", "supersedes", "clarifies"))
        assert all(re.match(r"^Q-\d{3}$", q) for q in fields["questions"])
        assert "\n## Claim\n" in text and "\n## Passage\n\n> " in text
