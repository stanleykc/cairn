"""Performance goals for `ingest.py` (003 plan, Performance Goals).

- `status` and `verify` (all sources) under 2 s with 50 sources and about 2,000 markdown files;
- `extract` of a 100-page text PDF or a 50-page Word document under 10 s.

Set `CAIRN_SLOW_MACHINE=1` to skip on slow machines.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "src" / "cairn" / "assets" / "skills" / "ingest" / "scripts" / "ingest.py"
HAS_POPPLER = all(shutil.which(t) for t in ("pdftotext", "pdfinfo", "pdfimages"))

pytestmark = pytest.mark.skipif(os.environ.get("CAIRN_SLOW_MACHINE") == "1",
                                reason="CAIRN_SLOW_MACHINE=1 skips timing tests")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ingest = _load("perf_ingest", SCRIPT)
make = _load("perf_make", REPO / "tests" / "fixtures" / "ingest" / "make_fixtures.py")


def inproc(eng: Path, *args) -> int:
    with contextlib.redirect_stdout(io.TextIOWrapper(io.BytesIO())):
        return ingest.main(["--root", str(eng), *args])


def timed(eng: Path, *args) -> tuple:
    start = time.perf_counter()
    result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(eng), *args], capture_output=True)
    return result.returncode, time.perf_counter() - start


@pytest.fixture(scope="module")
def big_engagement(tmp_path_factory) -> Path:
    work = tmp_path_factory.mktemp("perf")
    subprocess.run([sys.executable, "-m", "cairn", "init", "--no-git", "--engagement", "Fulfillment Review",
                    "--client", "Acme", "--code-name", "Northwind", "--lead", "Test Lead",
                    "--start-date", "2026-11-03"], cwd=work, check=True, capture_output=True)
    [eng] = [p for p in work.iterdir() if p.is_dir()]
    record = eng / "engagement.md"
    record.write_text(re.sub(r"^model_use: .*$", "model_use: allowed", record.read_text(), flags=re.M))
    raw = eng / "10-sources" / "raw"
    for n in range(50):
        kind = n % 3
        if kind == 0:
            (raw / f"note-{n}.md").write_text(make.CLIENT_PROCESS + f"\nRevision note {n}.\n")
        elif kind == 1:
            (raw / f"call-{n}.vtt").write_text(
                "WEBVTT\n\n" + "\n".join(f"00:00:{i:02d}.000 --> 00:00:{i:02d}.900\n<v Speaker {i % 3}>Line {i} of call {n}.\n"
                                        for i in range(40)))
        else:
            (raw / f"site-{n}.txt").write_text(make.SITE_NOTES + f"\nVisit {n}.\n")
    for path in sorted(p for p in raw.iterdir() if not p.name.startswith(".")):
        assert inproc(eng, "extract", path.name) == 0
    for src in sorted((eng / "10-sources" / "extracted").glob("S-*.md")):
        text = src.read_text()
        text = re.sub(r'^title: ""', f'title: "Source {src.stem} (Northwind)"', text, count=1, flags=re.M)
        text = re.sub(r'^provided_by: ""', 'provided_by: "Ops team"', text, count=1, flags=re.M)
        text = re.sub(r'^meeting_date: ""', 'meeting_date: "2026-10-20"', text, count=1, flags=re.M)
        src.write_text(text)
        assert inproc(eng, "finalize", src.stem) == 0
    folders = ["30-observations", "40-synthesis/findings", "_inbox", "20-research", "70-views"]
    for i in range(1950):
        folder = eng / folders[i % len(folders)]
        (folder / f"X-{i:04d}.md").write_text(
            f'---\nid: "O-{i:04d}"\ntype: observation\nsource: "S-{(i % 50) + 1:03d}"\n---\n\nObservation {i}.\n')
    return eng


def test_status_and_verify_under_two_seconds(big_engagement):
    code, seconds = timed(big_engagement, "status")
    assert code == 0 and seconds < 2.0, seconds
    code, seconds = timed(big_engagement, "verify")
    assert code == 0 and seconds < 2.0, seconds


@pytest.mark.skipif(not HAS_POPPLER, reason="poppler (pdftotext) is not installed")
def test_extract_100_page_pdf_under_ten_seconds(tmp_path, big_engagement):
    eng = tmp_path / "eng"
    shutil.copytree(big_engagement, eng)
    (eng / "10-sources" / "raw" / "long-100.pdf").write_bytes(make.build_pdf(make.long_pages(100)))
    code, seconds = timed(eng, "extract", "long-100.pdf")
    assert code == 0 and seconds < 10.0, seconds


def test_extract_50_page_word_under_ten_seconds(tmp_path, big_engagement):
    eng = tmp_path / "eng"
    shutil.copytree(big_engagement, eng)
    body = "".join(make.para(f"Section {i}", "Heading1") + "".join(
        make.para(f"Paragraph {j} of section {i}: inbound volume was within the planned range at the north sites.")
        for j in range(12)) + make.table([[make.cell("Site"), make.cell("Orders")], [make.cell("North"), make.cell(str(i))]])
        for i in range(50))
    (eng / "10-sources" / "raw" / "long-50.docx").write_bytes(make.build_docx(body))
    code, seconds = timed(eng, "extract", "long-50.docx")
    assert code == 0 and seconds < 10.0, seconds
