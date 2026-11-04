"""Golden synthetic charters: `charter.py status` and `check` give the expected results (SC-003, SC-004)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PACKAGE_ASSETS

SCRIPT = PACKAGE_ASSETS / "skills" / "charter" / "scripts" / "charter.py"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "charter"
ALL_SECTIONS = ("Objectives", "In scope", "Out of scope", "Deliverables", "Timeline", "Constraints")

EXPECTED = {
    "empty": {
        "ok": True, "state": "empty", "next": ("Q-001", "H-001", "A-001"), "problems": [],
        "gaps": [("scope-section-empty", s) for s in ALL_SECTIONS]
                + [("no-stakeholders", None), ("no-lenses", None)],
        "pending": [], "proposed_since_approval": 0,
    },
    "drafted": {
        "ok": True, "state": "draft", "next": ("Q-004", "H-003", "A-002"), "problems": [],
        "gaps": [("question-no-hypothesis", "Q-003")],
        "pending": [], "proposed_since_approval": 0,
    },
    "approved": {
        "ok": True, "state": "approved", "next": ("Q-005", "H-004", "A-003"), "problems": [],
        "gaps": [("question-no-hypothesis", "Q-003"), ("question-no-hypothesis", "Q-004")],
        "pending": [], "proposed_since_approval": 0,
    },
    "revised": {
        "ok": True, "state": "approved", "next": ("Q-006", "H-006", "A-003"), "problems": [],
        "gaps": [("question-no-hypothesis", "Q-003"), ("question-no-hypothesis", "Q-004"),
                 ("question-no-hypothesis", "Q-005")],
        "pending": [{"new": "H-005", "old": "H-003"}], "proposed_since_approval": 2,
    },
    "codename": {
        "ok": True, "state": "draft", "next": ("Q-002", "H-002", "A-001"), "problems": [],
        "gaps": [("scope-section-empty", s) for s in ALL_SECTIONS]
                + [("no-stakeholders", None), ("no-lenses", None)],
        "pending": [], "proposed_since_approval": 0,
    },
    "broken": {
        "ok": False, "state": "approved", "next": ("Q-100", "H-006", "A-004"),
        "problems": sorted([
            "duplicate-id", "malformed-id", "hypothesis-question", "one-way-link", "client-ready",
            "cited-source", "reject-state", "supersede-state", "approved-unconfirmed",
        ]),
        "gaps": [], "pending": [], "proposed_since_approval": 11,
    },
}


def run(root: Path, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          capture_output=True, text=True)


def copy(tmp_path: Path, name: str) -> Path:
    dest = tmp_path / name
    shutil.copytree(FIXTURES / name, dest)
    return dest


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_golden(tmp_path, name):
    want = EXPECTED[name]
    root = copy(tmp_path, name)

    check = run(root, "check")
    assert check.returncode == (0 if want["ok"] else 1), check.stderr
    check_out = json.loads(check.stdout)
    assert check_out["ok"] is want["ok"]
    assert sorted(p["code"] for p in check_out["problems"]) == want["problems"]

    result = run(root, "status")
    assert result.returncode == 0, result.stderr
    status = json.loads(result.stdout)
    assert status["charter"]["state"] == want["state"]
    assert tuple(status["next_ids"].values()) == want["next"]
    assert sorted(p["code"] for p in status["problems"]) == want["problems"]
    gaps = [(g["code"], g.get("id") or g.get("section")) for g in status["gaps"]]
    assert gaps == want["gaps"]
    assert status["pending_revisions"] == want["pending"]
    assert status["proposed_since_approval"] == want["proposed_since_approval"]


def test_every_item_well_formed_in_clean_fixtures(tmp_path):
    for name in ("drafted", "approved", "revised", "codename"):
        status = json.loads(run(copy(tmp_path, name), "status").stdout)
        for item in status["items"]:
            assert item["status"] in ("proposed", "active", "superseded", "rejected")
            assert item["origin"] == "consultant-note"


# --- US2: code name and model use ------------------------------------------------------


def test_codename_label(tmp_path):
    result = run(copy(tmp_path, "codename"), "status")
    engagement = json.loads(result.stdout)["engagement"]
    assert engagement["client_label"] == "Northwind"
    assert engagement["uses_code_name"] is True
    assert "globex" not in result.stdout.lower()


def test_codename_leak_detected(tmp_path):
    root = copy(tmp_path, "codename")
    with open(root / "00-charter" / "questions.md", "a") as fh:
        fh.write("\nNotes from Globex kickoff.\n")
    for command in ("check", "status"):
        result = run(root, command)
        assert "globex" not in result.stdout.lower()
        problems = json.loads(result.stdout)["problems"]
        assert [(p["code"], p["file"]) for p in problems] == [("real-name-leak", "00-charter/questions.md")]


def test_drafted_notes_mismatch(tmp_path):
    root = copy(tmp_path, "drafted")
    scope = root / "00-charter" / "scope.md"
    scope.write_text(scope.read_text().replace(
        'model_use_notes: "No interview transcripts to external AI"', 'model_use_notes: "Edited by hand"'))
    result = run(root, "check")
    assert result.returncode == 1
    assert [p["code"] for p in json.loads(result.stdout)["problems"]] == ["model-use-mismatch"]
