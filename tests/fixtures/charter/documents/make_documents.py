#!/usr/bin/env python3
"""Generate the synthetic engagement documents used by the charter tests and evals.

    python3 tests/fixtures/charter/documents/make_documents.py [OUTDIR]

Writes every document into OUTDIR (default: this folder) and prints the names written.
The outputs are committed. Tests copy them into a test copy's `10-sources/raw/`; they are
never committed under a fixture's `10-sources/`.

Every word is synthetic (constitution Principle VIII): clients "Acme" and "Globex", code
name "Northwind", lead "Test Lead". The PDF and Word builders come from the ingest fixture
generator (imported, not copied).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ingest"))

from make_fixtures import (  # noqa: E402
    SCANNED_PAGES, build_docx, build_pdf, cell, para, table, write_text_fixture,
)

# One source of truth for the SOW, so the .md, .pdf and .docx carry the same content.
# Objectives, boundaries, deliverables, timeline and stakeholders are covered; there is
# deliberately no hypotheses or lenses section. The "Background" sentence reads as a fact
# but is a hunch, so the skill should offer it as a hypothesis or assumption.
SOW_TITLE = "Statement of Work: Fulfillment Review"
SOW_SECTIONS: List[tuple] = [
    ("Background", [
        "Acme engaged Test Lead to review fulfillment in the north region.",
        "Carrier pickup delays are the main cause of late shipments.",
    ]),
    ("Objectives", [
        "- Cut order-to-ship time by 30% in the north DCs.",
        "- Recommend a fulfillment operating model the client can run without new headcount.",
    ]),
    ("In scope", [
        "- The three north-region distribution centers.",
        "- Order release, picking, packing and carrier handoff.",
    ]),
    ("Out of scope", [
        "- Inbound supplier logistics.",
        "- Store replenishment.",
    ]),
    ("Deliverables", [
        "- Diagnostic readout, slide deck, due 2026-11-20.",
        "- Final recommendations, report and deck, due date to be agreed.",
    ]),
    ("Timeline", [
        "- 2026-11-03: Kickoff.",
        "- 2026-11-20: Diagnostic readout.",
        "- 2026-12-04: Final readout.",
    ]),
]
SOW_STAKEHOLDERS = [
    ("Name", "Role"),
    ("Pat Sponsor", "VP Operations, sponsor"),
    ("Sam Planner", "North DC operations lead"),
]


def sow_markdown(client: str = "Acme") -> str:
    lines = [f"# {SOW_TITLE}", ""]
    for heading, body in SOW_SECTIONS:
        lines += [f"## {heading}", ""] + [b.replace("Acme", client) for b in body] + [""]
    lines += ["## Stakeholders", ""]
    header, *rows = SOW_STAKEHOLDERS
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def sow_pdf() -> bytes:
    pages: List[dict] = []
    texts: List[tuple] = []
    y = 740

    def put(size: int, text: str) -> None:
        nonlocal y, texts
        if y < 80:
            pages.append({"text": texts})
            texts, y = [], 740
        texts.append((72, y, size, text))
        y -= size + 8

    put(16, SOW_TITLE)
    for heading, body in SOW_SECTIONS:
        put(13, heading)
        for line in body:
            put(11, line)
    put(13, "Stakeholders")
    for row in SOW_STAKEHOLDERS:
        put(11, "    ".join(row))
    pages.append({"text": texts})
    return build_pdf(pages)


def sow_docx(client: str = "Acme") -> bytes:
    body = para(SOW_TITLE, style="Title")
    for heading, lines in SOW_SECTIONS:
        body += para(heading, style="Heading1")
        for line in lines:
            body += para(line.lstrip("- ").replace("Acme", client))
    body += para("Stakeholders", style="Heading1")
    body += table([[cell(c) for c in row] for row in SOW_STAKEHOLDERS])
    return build_docx(body)


CHANGE_ORDER = """# Change Order 1: Fulfillment Review

Applies to the Statement of Work dated 2026-11-03.

## Changes

- The final readout moves from 2026-12-04 to 2026-12-11, because the client's leadership
  offsite moved.
- New deliverable: carrier scorecard, spreadsheet, due 2026-12-11.

Everything else in the Statement of Work is unchanged.
"""


def _write_bytes(data_fn: Callable[[], bytes]) -> Callable[[Path], None]:
    return lambda path: path.write_bytes(data_fn())


DOCUMENTS: Dict[str, Callable[[Path], None]] = {
    "sow-synthetic.md": lambda p: write_text_fixture(p, sow_markdown()),
    "sow-synthetic.pdf": _write_bytes(sow_pdf),
    "sow-synthetic.docx": _write_bytes(sow_docx),
    "sow-globex.md": lambda p: write_text_fixture(p, sow_markdown("Globex")),
    "sow-globex.docx": _write_bytes(lambda: sow_docx("Globex")),
    "change-order-synthetic.md": lambda p: write_text_fixture(p, CHANGE_ORDER),
    "sow-scanned.pdf": _write_bytes(lambda: build_pdf([{"image": lines} for lines in SCANNED_PAGES])),
    "sow-encrypted.pdf": _write_bytes(
        lambda: build_pdf([{"text": [(72, 700, 12, "Locked statement of work")]}], encrypt=True)),
    "sow-legacy.doc": _write_bytes(lambda: bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 504),
}


def write(outdir: Path) -> list:
    outdir.mkdir(parents=True, exist_ok=True)
    for name, writer in DOCUMENTS.items():
        writer(outdir / name)
    return list(DOCUMENTS)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    outdir = Path(argv[0]) if argv else HERE
    for name in write(outdir):
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
