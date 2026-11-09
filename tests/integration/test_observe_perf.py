"""`observe.py` timing goals (005 plan, Performance Goals): `status`, `prepare` and `verify` finish
in under 2 s on an engagement with 50 sources and 2,000 observations, and `add` of a 40-draft
file in under 2 s.

Set `CAIRN_SLOW_MACHINE=1` to skip on slow machines.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "src" / "cairn" / "assets" / "skills" / "extract-observations" / "scripts" / "observe.py"
GOLDEN = REPO / "tests" / "fixtures" / "observe" / "golden" / "us1"
LIMIT = 2.0
SOURCES = 50
OBSERVATIONS = 2000

pytestmark = pytest.mark.skipif(os.environ.get("CAIRN_SLOW_MACHINE") == "1",
                                reason="CAIRN_SLOW_MACHINE=1: timing goals are not meaningful on this machine")


@pytest.fixture(scope="module")
def big(tmp_path_factory) -> Path:
    work = tmp_path_factory.mktemp("perf")
    subprocess.run([sys.executable, "-m", "cairn", "init", "--no-git", "--engagement", "Fulfillment Review",
                    "--client", "Acme", "--code-name", "Northwind", "--lead", "Test Lead",
                    "--start-date", "2026-11-03"], cwd=work, check=True, capture_output=True)
    [eng] = [p for p in work.iterdir() if p.is_dir()]
    shutil.copytree(GOLDEN, eng, dirs_exist_ok=True, ignore=shutil.ignore_patterns("expected", "drafts*.json", "10-sources"))
    text = (eng / "engagement.md").read_text()
    (eng / "engagement.md").write_text(re.sub(r"^model_use: \w+", "model_use: allowed", text, flags=re.M))
    extracted = eng / "10-sources" / "extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    originals = sorted((GOLDEN / "10-sources" / "extracted").glob("S-*.md"))
    for n in range(1, SOURCES + 1):
        template = originals[(n - 1) % len(originals)].read_text()
        sid = f"S-{n:03d}"
        (extracted / f"{sid}.md").write_text(re.sub(r'^id: "S-\d+"', f'id: "{sid}"', template, count=1, flags=re.M))
    expected = {p.stem: p.read_text() for p in sorted((GOLDEN / "expected").glob("O-*.md"))}
    by_source = {}
    for text in expected.values():
        sid = re.search(r'^source: "(S-\d+)"', text, re.M).group(1)
        by_source.setdefault(sid, []).append(text)
    inbox, kept = eng / "_inbox", eng / "30-observations"
    kind = {f"S-{n:03d}": originals[(n - 1) % len(originals)].stem for n in range(1, SOURCES + 1)}
    targets = [sid for sid in sorted(kind) if kind[sid] in by_source]
    for n in range(1, OBSERVATIONS + 1):
        target = targets[n % len(targets)]
        candidates = by_source[kind[target]]
        text = candidates[(n // len(targets)) % len(candidates)]
        oid = f"O-{n:04d}"
        text = re.sub(r'^id: "O-\d+"', f'id: "{oid}"', text, count=1, flags=re.M)
        text = re.sub(r'^source: "S-\d+"', f'source: "{target}"', text, count=1, flags=re.M)
        folder = inbox if n % 2 else kept
        (folder / f"{oid}.md").write_text(text)
    drafts = []
    for n in range(40):
        drafts.append({"source": "S-001", "locator": f"p. {2 + n % 2}",
                       "quote": ["Order-to-ship time rose in both northern sites during Q3.",
                                 "Review carrier pickup windows with the transport team."][n % 2],
                       "claim": f"Synthetic claim number {n} about the review.", "title": f"Synthetic claim {n}",
                       "questions": ["Q-003"], "confidence": "medium", "confidence_reason": "synthetic",
                       "accept_warnings": ["same-passage"]})
    work_dir = eng / ".cairn" / "work" / "extract-observations"
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "drafts-perf.json").write_text(json.dumps({"drafts": drafts}))
    return eng


def timed(eng: Path, *args) -> tuple:
    start = time.monotonic()
    result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(eng), *args], capture_output=True, text=True)
    return time.monotonic() - start, result


@pytest.mark.parametrize("args", [["status"], ["prepare", "S-001"], ["verify"]], ids=["status", "prepare", "verify"])
def test_read_commands_under_two_seconds(big, args):
    elapsed, result = timed(big, *args)
    assert result.returncode == 0, result.stdout[:2000]
    if args == ["verify"]:
        assert json.loads(result.stdout)["checked"] == OBSERVATIONS
    assert elapsed < LIMIT, f"{args[0]} took {elapsed:.2f}s"


def test_add_forty_drafts_under_two_seconds(big):
    elapsed, result = timed(big, "add", ".cairn/work/extract-observations/drafts-perf.json", "--dry-run")
    assert result.returncode == 0, result.stdout[:2000]
    out = json.loads(result.stdout)
    assert len(out["written"]) == 40, out["refused"][:3]
    assert elapsed < LIMIT, f"add took {elapsed:.2f}s"
