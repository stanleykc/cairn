"""Golden synthetic engagements: `extract` + the assistant's edits + `finalize` give the expected
sources, `verify` passes on them and catches a changed word (SC-003–SC-005)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "src" / "cairn" / "assets" / "skills" / "ingest" / "scripts" / "ingest.py"
GOLDEN = REPO / "tests" / "fixtures" / "ingest" / "golden"
HAS_PDFTOTEXT = all(shutil.which(t) for t in ("pdftotext", "pdfinfo", "pdfimages"))
CANARY = "CANARY-ingest-91c2"

spec = importlib.util.spec_from_file_location("golden_make", REPO / "tests" / "fixtures" / "ingest" / "make_fixtures.py")
make = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make)

# case → originals in extraction order (S-001, S-002, …)
CASES = {
    "us1": ["text-table-chart.pdf", "scanned.pdf", "hard-page.pdf", "process-manual.docx"],
    "us2": ["kickoff-transcript.md", "kickoff.vtt", "weekly-summary.md", "client-process.md"],
}
# A word inside each case's content that `verify` must notice, and its locator.
MUTATIONS = {
    "us1": ("S-001", "rose in both", "fell in both", "p. 2"),
    "us2": ("S-004", "door 7", "door 9", "§ Returns process"),
}


def run(eng: Path, *args) -> tuple:
    result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(eng), *args], capture_output=True, text=True)
    run.stdout = result.stdout
    return result.returncode, json.loads(result.stdout)


def raw_hashes(eng: Path) -> dict:
    raw = eng / "10-sources" / "raw"
    out = {}
    for p in sorted(raw.rglob("*")):
        if p.is_file():
            try:
                out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
            except PermissionError:
                out[p.name] = f"unreadable:{p.stat().st_size}"
    return out


def tree(eng: Path) -> dict:
    return {p.relative_to(eng).as_posix(): p.read_bytes() for p in sorted(eng.rglob("*"))
            if p.is_file() and "10-sources/raw" not in p.as_posix() and ".cairn/" not in p.relative_to(eng).as_posix()}


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
    shutil.copytree(GOLDEN / case, eng, dirs_exist_ok=True, ignore=shutil.ignore_patterns("expected"))
    return eng


def without(text: str, *fields) -> str:
    for field in fields:
        text = re.sub(rf"^{field}:.*$", f"{field}: <ignored>", text, flags=re.M)
    return text


@pytest.mark.parametrize("case", sorted(CASES))
def test_golden_case(tmp_path, case):
    names = CASES[case]
    if case == "us1" and not HAS_PDFTOTEXT:
        pytest.skip("the us1 golden case has PDFs and needs pdftotext (poppler)")
    eng = golden_engagement(tmp_path, case)
    make.write(eng / "10-sources" / "raw", names)
    before = raw_hashes(eng)
    expected = GOLDEN / case / "expected"
    for n, name in enumerate(names, start=1):
        code, out = run(eng, "extract", name)
        assert code == 0, out
        sid = out["id"]
        assert sid == f"S-{n:03d}"
        draft = (eng / out["file"]).read_text()
        sha = re.search(r"^raw_sha256: .*$", draft, re.M).group(0)
        created = re.search(r"^created: .*$", draft, re.M).group(0)
        text = (expected / f"{sid}.md").read_text()
        # The assistant's version of the draft: everything as expected, before finalize.
        text = re.sub(r"^raw_sha256: .*$", sha, text, flags=re.M)
        text = re.sub(r"^created: .*$", created, text, flags=re.M)
        text = text.replace("extraction_status: complete", "extraction_status: in-progress")
        text = text.replace("fidelity: checked", "fidelity: pending")
        (eng / out["file"]).write_text(text)
        code, out = run(eng, "finalize", sid)
        assert code == 0, out
    code, out = run(eng, "verify")
    assert code == 0, out
    for n in range(1, len(names) + 1):
        sid = f"S-{n:03d}"
        got = (eng / "10-sources" / "extracted" / f"{sid}.md").read_text()
        want = (expected / f"{sid}.md").read_text()
        assert without(got, "created", "raw_sha256") == without(want, "created", "raw_sha256"), sid
    assert (eng / "10-sources" / "index.md").read_text() == (expected / "index.md").read_text()
    assert raw_hashes(eng) == before

    sid, old, new, locator = MUTATIONS[case]
    path = eng / "10-sources" / "extracted" / f"{sid}.md"
    path.write_text(path.read_text().replace(old, new, 1))
    code, out = run(eng, "verify")
    assert code == 1
    mismatches = [p for p in out["problems"] if p["code"] == "content-mismatch"]
    assert [(p["id"], p["locator"]) for p in mismatches] == [(sid, locator)]
    assert new.split()[0] not in run.stdout


def test_golden_us3_restricted(tmp_path):
    eng = golden_engagement(tmp_path, "us3")
    raw = eng / "10-sources" / "raw"
    make.write(raw, ["client-process.md"])
    hr = raw / "hr-attrition.md"
    hr.write_text(f"# HR attrition\n\n{CANARY} attrition by site.\n")
    hr.chmod(0)
    outputs = []
    try:
        code, out = run(eng, "extract", "hr-attrition.md")
        assert code == 3
        outputs.append(run.stdout)
        code, out = run(eng, "register-restricted", "hr-attrition.md", "--title", "HR attrition report (Northwind)",
                        "--material", "document", "--source-date", "2026-10", "--provided-by", "HR lead")
        assert code == 0, out
        outputs.append(run.stdout)
        code, out = run(eng, "extract", "client-process.md")
        assert code == 3 and out["refused"] == "policy-restricted-needs-consent"
        code, out = run(eng, "extract", "client-process.md", "--sendable")
        assert code == 0
        sid = out["id"]
        path = eng / out["file"]
        text = path.read_text()
        text = re.sub(r'^title: .*$', 'title: "Returns process (Northwind)"', text, count=1, flags=re.M)
        text = re.sub(r'^provided_by: .*$', 'provided_by: "Operations team"', text, count=1, flags=re.M)
        path.write_text(text)
        for args in (("finalize", sid), ("verify",), ("status",), ("review", "S-001", sid), ("refs", "S-001")):
            code, out = run(eng, *args)
            assert code == 0, (args, out)
            outputs.append(run.stdout)
    finally:
        hr.chmod(0o644)
    assert all(CANARY not in o for o in outputs)
    for rel, data in tree(eng).items():
        assert CANARY.encode() not in data, rel
    index = (eng / "10-sources" / "index.md").read_text()
    assert "| S-001 | HR attrition report (Northwind) | document | 2026-10 | client-document | proposed | yes |" in index


@pytest.mark.skipif(not HAS_PDFTOTEXT, reason="the us4 golden case has PDFs and needs pdftotext (poppler)")
def test_golden_us4_review_and_fix(tmp_path):
    eng = golden_engagement(tmp_path, "us4")
    make.write(eng / "10-sources" / "raw", ["scanned.pdf", "text-table-chart.pdf", "client-process.md"])
    code, out = run(eng, "verify")
    assert code == 0, out
    code, out = run(eng, "review", "S-001", "S-002", "S-003")
    assert code == 0
    s1 = out["sources"][0]
    assert s1["id"] == "S-001" and [d["kind"] for d in s1["derived"]] == ["ocr", "ocr"]
    assert {u["locator"] for u in s1["uncertain"]} == {"p. 1", "p. 2"}
    assert out["sources"][1]["tables"][0]["built_by"] == "assistant"
    before = tree(eng)

    # The consultant: "p. 1 should say WMS not VMS", then "approve S-001".
    path = eng / "10-sources" / "extracted" / "S-001.md"
    old = "> [!derived] ocr\n> APPENDIX: METHOD.\n> FIGURES ARE TAKEN FROM THE VMS\n> SHIPMENT LOG, EXCLUDING RETURNS.\n"
    new = ("> [!derived] ocr\n> APPENDIX: METHOD.\n\n> [!corrected] 2026-11-07 · derived\n"
           "> was: FIGURES ARE TAKEN FROM THE VMS\n> FIGURES ARE TAKEN FROM THE WMS\n\n> [!derived] ocr\n"
           "> SHIPMENT LOG, EXCLUDING RETURNS.\n")
    path.write_text(path.read_text().replace(old, new, 1))
    log = eng / "60-log" / "changelog.md"
    log.write_text(log.read_text().replace(
        "No changes yet.", "2026-11-07 · S-001 @ p. 1 · extraction-fix · OCR misread WMS · -\n"
                           "> FIGURES ARE TAKEN FROM THE VMS"))
    code, out = run(eng, "set-status", "S-001", "active")
    assert code == 0 and out["log"] == []

    got = path.read_text()
    want = (GOLDEN / "us4" / "expected" / "S-001.md").read_text()
    assert without(got, "created") == without(want, "created")
    text = log.read_text()
    assert len(re.findall(r"^\d{4}-\d{2}-\d{2} · S-001 @ p\. 1 · extraction-fix · .* · -$", text, re.M)) == 1
    assert "\n> FIGURES ARE TAKEN FROM THE VMS" in text
    code, out = run(eng, "verify")
    assert code == 0, out
    assert out["warnings"] == []
    code, out = run(eng, "refs", "S-001")
    assert [r["id"] for r in out["refs"]["S-001"]] == ["O-001"]
    after = tree(eng)
    changed = sorted(rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel))
    assert changed == ["10-sources/extracted/S-001.md", "10-sources/index.md", "60-log/changelog.md"]
    assert "| S-001 | Scanned method appendix (Northwind) | document | 2026-09 | client-document | active | no |" \
        in (eng / "10-sources" / "index.md").read_text()
