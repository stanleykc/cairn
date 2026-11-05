#!/usr/bin/env python3
"""Helper for the `ingest` skill: list originals, extract them verbatim, check and record sources.

    python3 ingest.py [--root PATH] status [RAW ...]
    python3 ingest.py [--root PATH] extract RAW [--as {document,transcript}] [--sendable] [--restart]
    python3 ingest.py [--root PATH] register-restricted RAW [--title T] [--material M] [--source-date D] [--provided-by P]
    python3 ingest.py [--root PATH] verify [ID ...]
    python3 ingest.py [--root PATH] finalize ID
    python3 ingest.py [--root PATH] review ID [ID ...]
    python3 ingest.py [--root PATH] set-status ID {active,rejected} [--reason TEXT] [--trigger {new-evidence,client-feedback,rethinking}]
    python3 ingest.py [--root PATH] restrict ID --reason TEXT [--remove-content --by NAME]
    python3 ingest.py [--root PATH] refs ID [ID ...]
    python3 ingest.py --version

Contract: specs/003-ingest-skill/contracts/ingest-script.md. Python 3.9+, standard library
only, no network. PDFs are read with the local poppler tools (`pdftotext`, `pdfinfo`,
`pdfimages`) when they are on PATH ("checked" mode); without them the assistant copies the
text and the source is marked `fidelity: unchecked`.

Rules this script keeps:
- Nothing under `10-sources/raw/` is ever written, renamed, moved or deleted. Originals are
  opened read-only, only by `extract`, `verify` and `finalize`, only through
  `open_original()`, never while `model_use` is `unconfirmed`, and never for a restricted
  source.
- Stdout is one JSON object that never contains extracted text: only IDs, locators, labels,
  counts, paths and codes (speaker labels are the one exception). The real client name never
  appears in the output when a code name is set.
- Every write is atomic (temp file + `os.replace`).

It does not import `cairn` or `charter.py`: each engagement runs the copy pinned to its own
framework version. The parsing helpers are copied from `charter.py` and kept identical by a
parity test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPT_VERSION = "0.3.0"

EXIT_OK, EXIT_PROBLEMS, EXIT_NO_ENGAGEMENT = 0, 1, 2
EXIT_POLICY, EXIT_DUPLICATE, EXIT_CANT_EXTRACT, EXIT_USAGE = 3, 4, 5, 6

NOT_IN_ENGAGEMENT = (
    "Not inside a Cairn engagement. Create one with `cairn init`, then run `ingest` "
    "from inside it."
)

RAW_DIR = "10-sources/raw"
EXTRACTED_DIR = "10-sources/extracted"
INDEX = "10-sources/index.md"
CHANGELOG = "60-log/changelog.md"
WORK_DIR = ".cairn/work/ingest"

# The canonical layout minus `10-sources/` (and its subfolders) and `_templates/` (as charter).
CONTENT_FOLDERS = (
    "_inbox",
    "00-charter",
    "20-research",
    "30-observations",
    "40-synthesis",
    "40-synthesis/findings",
    "40-synthesis/issues",
    "40-synthesis/opportunities",
    "50-options",
    "60-log",
    "70-views",
    "80-deliverables",
)

FORMATS = {
    ".pdf": "pdf", ".docx": "docx", ".md": "markdown", ".markdown": "markdown",
    ".txt": "text", ".vtt": "vtt", ".srt": "srt",
}
POPPLER = ("pdftotext", "pdfinfo", "pdfimages")
INSTALL_HINT = "brew install poppler  |  apt install poppler-utils"
TOOL_TIMEOUT = 120

CONTENT_START = "<!-- cairn:content:start -->"
CONTENT_END = "<!-- cairn:content:end -->"
RESTRICTED_NOTICE = "Restricted: not extracted. Do not open the original with an AI tool."
DESCRIPTION_LABEL = "*Written by `ingest`. Not part of the source.*"
DEFAULT_CONFIDENCE_REASON = "trust not stated by the consultant"

FIELD_ORDER = (
    "id", "type", "title", "status", "origin", "confidence", "confidence_reason",
    "inference_confirmed", "audience", "supports", "contradicts", "derived_from",
    "supersedes", "clarifies", "change_reason", "change_trigger", "created",
    "material", "source_type", "raw_file", "raw_sha256", "raw_bytes", "provided_by",
    "source_date", "meeting_title", "meeting_date", "attendees", "author", "author_kind",
    "extraction_status", "fidelity", "extraction_method", "derived", "restricted",
    "content_removed", "page_count", "pages_reviewed", "uncertain_passages",
)
BOOL_FIELDS = ("inference_confirmed", "derived", "restricted", "content_removed")
INT_FIELDS = ("raw_bytes", "page_count", "pages_reviewed")
LIST_FIELDS = ("supports", "contradicts", "derived_from", "supersedes", "clarifies",
               "attendees", "uncertain_passages")
BARE_FIELDS = ("type", "status", "origin", "confidence", "audience", "material", "source_type",
               "extraction_status", "fidelity", "extraction_method", "author_kind")
REQUIRED = ("title", "material", "source_type", "raw_file", "raw_bytes", "provided_by",
            "confidence_reason")

MATERIALS = ("document", "meeting-transcript", "meeting-notes")
MEETINGS = ("meeting-transcript", "meeting-notes")
SOURCE_TYPES = ("pdf", "docx", "markdown", "text", "vtt", "srt", "deck", "spreadsheet",
                "image", "web", "other")
SOURCE_ORIGINS = ("client-document", "interview-meeting", "consultant-note",
                  "external-research", "prior-engagement")
ALLOWED = {
    "status": ("proposed", "active", "superseded", "rejected"),
    "confidence": ("high", "medium", "low"),
    "material": MATERIALS,
    "source_type": SOURCE_TYPES,
    "extraction_status": ("in-progress", "complete"),
    "fidelity": ("pending", "checked", "unchecked", ""),
    "extraction_method": ("text", "ocr", "vision-description", "mixed", "none"),
    "author_kind": ("", "person", "ai-notetaker"),
    "change_trigger": ("", "new-evidence", "client-feedback", "rethinking"),
}
TRIGGERS = ("new-evidence", "client-feedback", "rethinking")
REF_FIELDS = ("source", "derived_from", "supports", "contradicts", "supersedes", "clarifies")

ID_TOKEN = re.compile(r"^[A-Z]-\d{3,}$")
SOURCE_ID = re.compile(r"^S-\d{3,}$")
S_MENTION = re.compile(r"\bS-(\d{3,})\b")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
FULL_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_DATE = re.compile(r"^(\d{4}|\d{4}-\d{2}|\d{4}-\d{2}-\d{2})$")
YAML_FENCE = re.compile(r"^```\s*ya?ml\s*$")
STRICT_HEADING = re.compile(r"^## ([A-Z])-(\d{3,}): (\S.*)$")
LOOSE_HEADING = re.compile(r"^## ([A-Z]{1,3}-[^\s:]*)")
KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")
LIST_ITEM = re.compile(r"^\s*-(?:\s+(.*))?$")

# Markers inside the content region (data-model §3.4).
PAGE_MARK = re.compile(r"^### p\. (\d+)(?: \(printed: [^)]*\))?\s*$")
TURN_MARK = re.compile(r"^\*\*(.+?)\*\* \[T(\d+)(?: · (\d{2}:\d{2}:\d{2}))?\]:(?:\s(.*))?$")
PARA_MARK = re.compile(r"^\[¶(\d+)\](?:\s(.*))?$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
CALLOUT = re.compile(r"^>\s*\[!([\w-]+)\]\s*(.*)$")
UNIT_COMMENTS = {"<!-- cairn:footnotes -->": "footnotes", "<!-- cairn:comments -->": "comments"}
HTML_COMMENT = re.compile(r"^\s*<!--.*-->\s*$")
TABLE_SEPARATOR = re.compile(r"^\|?[\s:|-]+\|?$")
CELL_SPLIT = re.compile(r"(?<!\\)\|")
UNCERTAIN_LINE = re.compile(r"^-\s+(.+?)\s+—\s+(.*)$")
GENERIC_LABEL = re.compile(r"^(speaker|participant)\s*\d+$|^unknown(\s+speaker)?$|^\(unlabelled\)$", re.I)

RAW_READS = 0  # how many times an original was opened (tests assert zero when they must be)


class Fail(Exception):
    """Stop with an exit code and a JSON payload."""

    def __init__(self, code: int, payload):
        if isinstance(payload, str):
            payload = {"error": payload}
        super().__init__(json.dumps(payload))
        self.code = code
        self.payload = payload


# --- Parsing (copied from charter.py; keep identical, see test_ingest_parity.py) ---------


def _find_close_quote(s: str, quote: str) -> int:
    i = 1
    while i < len(s):
        c = s[i]
        if quote == '"' and c == "\\":
            i += 2
            continue
        if c == quote:
            if quote == "'" and s[i + 1 : i + 2] == "'":
                i += 2
                continue
            return i
        i += 1
    return -1


def _rest_ok(rest: str) -> bool:
    rest = rest.strip()
    return not rest or rest.startswith("#")


def parse_value(raw: str):
    """Parse a flat YAML value: quoted or bare scalar, or an inline list. Returns (value, error)."""
    s = raw.strip()
    if not s or s.startswith("#"):
        return "", None
    if s[0] in "\"'":
        end = _find_close_quote(s, s[0])
        if end < 0:
            return None, "unterminated quote"
        if not _rest_ok(s[end + 1 :]):
            return None, "text after a quoted value"
        if s[0] == '"':
            try:
                return json.loads(s[: end + 1]), None
            except ValueError:
                return None, "bad escape in a quoted value"
        return s[1:end].replace("''", "'"), None
    if s[0] == "[":
        items, i, cur, quote = [], 1, "", ""
        while i < len(s):
            c = s[i]
            if quote:
                cur += c
                if c == "\\" and quote == '"' and i + 1 < len(s):
                    cur += s[i + 1]
                    i += 1
                elif c == quote:
                    quote = ""
            elif c in "\"'":
                quote = c
                cur += c
            elif c == "[" or c == "{":
                return None, "nested list"
            elif c == ",":
                items.append(cur)
                cur = ""
            elif c == "]":
                items.append(cur)
                break
            else:
                cur += c
            i += 1
        else:
            return None, "unterminated list"
        if not _rest_ok(s[i + 1 :]):
            return None, "text after a list"
        result = []
        for item in items:
            if not item.strip():
                continue
            value, error = parse_value(item)
            if error:
                return None, error
            result.append(value)
        return result, None
    if s[0] == "{":
        return None, "nested mapping"
    hash_at = s.find(" #")
    if hash_at >= 0:
        s = s[:hash_at]
    return s.strip(), None


def parse_mapping(lines: list, first_line: int):
    """Parse flat `key: value` lines (block lists allowed). Returns (fields, [(line, error)])."""
    fields: dict = {}
    errors = []
    list_key = None
    for offset, line in enumerate(lines):
        lineno = first_line + offset
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item = LIST_ITEM.match(line)
        if item and list_key is not None:
            value, error = parse_value(item.group(1) or "")
            if error or isinstance(value, list):
                errors.append((lineno, error or "nested list"))
                continue
            if not isinstance(fields[list_key], list):
                fields[list_key] = []
            fields[list_key].append(value)
            continue
        match = KEY_LINE.match(line)
        if not match:
            errors.append((lineno, "not a `key: value` line"))
            list_key = None
            continue
        key, raw = match.group(1), match.group(2) or ""
        value, error = parse_value(raw)
        if error:
            errors.append((lineno, error))
            list_key = None
            continue
        fields[key] = value
        list_key = key if value == "" else None
    return fields, errors


def split_front_matter(lines: list):
    """Return (front matter lines, index of the first body line), or (None, 0)."""
    if not lines or lines[0].strip() != "---":
        return None, 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], i + 1
    return None, 0


def parse_file(text: str, rel: str) -> dict:
    """Front matter, `## <ID>: <title>` entries and problems for one markdown file."""
    lines = text.splitlines()
    problems = []
    fm_lines, body = split_front_matter(lines)
    front: dict = {}
    if fm_lines is not None:
        front, errors = parse_mapping(fm_lines, 2)
        problems += [_problem("unparseable", None, rel, n, f"front matter: {e}") for n, e in errors]
    entries = []
    i, in_fence = body, False
    while i < len(lines):
        line = lines[i]
        if line.startswith(("```", "~~~")):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence or not line.startswith("## "):
            i += 1
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        has_yaml = j < len(lines) and bool(YAML_FENCE.match(lines[j]))
        loose = LOOSE_HEADING.match(line)
        if not has_yaml and not loose:
            i += 1
            continue
        strict = STRICT_HEADING.match(line)
        if strict:
            entry_id, title = f"{strict.group(1)}-{strict.group(2)}", strict.group(3).strip()
        else:
            entry_id = loose.group(1) if loose else line[3:].strip()
            title = line[3:].partition(":")[2].strip()
        entry = {
            "id": entry_id, "title": title, "fields": {}, "file": rel, "line": i + 1,
            "well_formed": bool(strict), "parsed": False,
        }
        entries.append(entry)
        if not has_yaml:
            problems.append(_problem("unparseable", entry_id, rel, i + 1, "no yaml block under the heading"))
            i += 1
            continue
        k = j + 1
        while k < len(lines) and not lines[k].startswith("```"):
            k += 1
        if k >= len(lines):
            problems.append(_problem("unparseable", entry_id, rel, j + 1, "yaml block is not closed"))
            break
        fields, errors = parse_mapping(lines[j + 1 : k], j + 2)
        entry["fields"] = fields
        entry["parsed"] = not errors
        problems += [_problem("unparseable", entry_id, rel, n, e) for n, e in errors]
        i = k + 1
    return {"front": front, "entries": entries, "problems": problems, "lines": lines, "body": body}


def _problem(code, id_, file, line, detail) -> dict:
    return {"code": code, "id": id_, "file": file, "line": line, "detail": detail}


def as_list(value) -> list:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v]
    if isinstance(value, str) and value:
        return [value]
    return []


def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def is_engagement(folder: Path) -> bool:
    text = read_text(folder / "engagement.md")
    if text is None:
        return False
    fm_lines, _ = split_front_matter(text.splitlines())
    if fm_lines is None:
        return False
    fields, _ = parse_mapping(fm_lines, 2)
    return fields.get("type") == "engagement"


def find_root(root_arg, cwd=None, script_path=__file__) -> Path:
    """The engagement root: --root, else walk up from cwd, else the script's own engagement."""
    if root_arg:
        root = Path(root_arg).resolve()
        if is_engagement(root):
            return root
        raise Fail(EXIT_NO_ENGAGEMENT, NOT_IN_ENGAGEMENT)
    start = Path(cwd or os.getcwd()).resolve()
    for folder in (start, *start.parents):
        if is_engagement(folder):
            return folder
    parents = Path(script_path).resolve().parents
    if len(parents) >= 5 and is_engagement(parents[4]):
        return parents[4]
    raise Fail(EXIT_NO_ENGAGEMENT, NOT_IN_ENGAGEMENT)


def append_changelog(text: str, line: str) -> str:
    lines = text.split("\n")
    for i, existing in enumerate(lines):
        if existing.strip() == "No changes yet.":
            lines[i] = line
            return "\n".join(lines)
    body = text if text.endswith("\n") or not text else text + "\n"
    return body + line + "\n"


def atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        try:
            os.chmod(tmp, path.stat().st_mode & 0o777)
        except OSError:
            pass
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _str(value) -> str:
    return value if isinstance(value, str) else ""


# --- Sources --------------------------------------------------------------------------------


def _bool(value) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def _int(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and re.match(r"^\d+$", value.strip()):
        return int(value.strip())
    return None


class Source:
    """One `10-sources/extracted/S-###.md` file: front matter, body sections, content region."""

    def __init__(self, path: Path, rel: str, text: str):
        self.path, self.rel, self.text = path, rel, text
        self.lines = text.split("\n")
        fm, body = split_front_matter(self.lines)
        self.fm_ok = fm is not None
        self.fields, self.fm_errors = parse_mapping(fm, 2) if fm is not None else ({}, [])
        self.body_start = body
        self.stem = path.stem
        self.id = _str(self.fields.get("id")) or self.stem
        starts = [i for i, l in enumerate(self.lines) if l.strip() == CONTENT_START]
        ends = [i for i, l in enumerate(self.lines) if l.strip() == CONTENT_END]
        self.c_start = starts[0] if len(starts) == 1 else None
        self.c_end = ends[0] if len(ends) == 1 else None
        if self.c_start is not None and (self.c_end is None or self.c_end <= self.c_start):
            self.c_start = self.c_end = None
        self.sections = {}
        current, start = None, None
        for i in range(self.body_start, len(self.lines)):
            if self.c_start is not None and self.c_start <= i <= self.c_end:
                continue
            if self.lines[i].startswith("## "):
                if current is not None:
                    self.sections[current] = (start, i)
                current, start = self.lines[i][3:].strip(), i
        if current is not None:
            end = self.c_start if self.c_start is not None and self.c_start > start else len(self.lines)
            self.sections[current] = (start, end)

    # field access
    def f(self, key: str) -> str:
        return _str(self.fields.get(key)).strip()

    def b(self, key: str) -> bool:
        return _bool(self.fields.get(key))

    def i(self, key: str):
        return _int(self.fields.get(key))

    def l(self, key: str) -> list:
        return as_list(self.fields.get(key))

    @property
    def has_markers(self) -> bool:
        return self.c_start is not None

    def content_lines(self) -> list:
        if not self.has_markers:
            return []
        return self.lines[self.c_start + 1 : self.c_end]

    def content_first_line(self) -> int:
        """1-based line number of the first content line."""
        return (self.c_start or 0) + 2

    def section_lines(self, name: str) -> list:
        if name not in self.sections:
            return []
        start, end = self.sections[name]
        return self.lines[start + 1 : end]

    def outside_content(self):
        """(1-based line, section name, text) for every line outside the content region."""
        section = "front matter"
        for i, line in enumerate(self.lines):
            if self.c_start is not None and self.c_start <= i <= self.c_end:
                continue
            if i >= self.body_start and line.startswith("## "):
                section = line[3:].strip()
            yield i + 1, section, line

    @property
    def complete(self) -> bool:
        return self.f("extraction_status") == "complete"

    @property
    def restricted(self) -> bool:
        return self.b("restricted")

    @property
    def is_meeting(self) -> bool:
        return self.f("material") in MEETINGS


def render_value(key: str, value) -> str:
    if key in BOOL_FIELDS:
        return "true" if _bool(value) else "false"
    if key in INT_FIELDS:
        n = _int(value)
        if n is not None:
            return str(n)
        # Keep a bad value visible (verify reports it) rather than turning it into 0.
        return "0" if value in (None, "") else json.dumps(_str(value), ensure_ascii=False)
    if key in LIST_FIELDS or isinstance(value, list):
        return "[" + ", ".join(json.dumps(v, ensure_ascii=False) for v in as_list(value)) + "]"
    s = _str(value) if not isinstance(value, (int, bool)) else str(value)
    if key in BARE_FIELDS and re.match(r"^[a-z][a-z-]*$", s):
        return s
    return json.dumps(s, ensure_ascii=False)


def render_front_matter(fields: dict) -> list:
    keys = list(FIELD_ORDER) + [k for k in fields if k not in FIELD_ORDER]
    return ["---"] + [f"{k}: {render_value(k, fields.get(k, ''))}" for k in keys if k in fields or k in FIELD_ORDER] + ["---"]


def default_fields(id_: str) -> dict:
    return {
        "id": id_, "type": "source", "title": "", "status": "proposed", "origin": "",
        "confidence": "medium", "confidence_reason": DEFAULT_CONFIDENCE_REASON,
        "inference_confirmed": False, "audience": "internal", "supports": [], "contradicts": [],
        "derived_from": [], "supersedes": [], "clarifies": [], "change_reason": "",
        "change_trigger": "", "created": date.today().isoformat(), "material": "",
        "source_type": "", "raw_file": "", "raw_sha256": "", "raw_bytes": 0, "provided_by": "",
        "source_date": "", "meeting_title": "", "meeting_date": "", "attendees": [], "author": "",
        "author_kind": "", "extraction_status": "in-progress", "fidelity": "pending",
        "extraction_method": "text", "derived": False, "restricted": False,
        "content_removed": False, "page_count": 0, "pages_reviewed": 0, "uncertain_passages": [],
    }


def render_body(speakers, uncertain: list, content: str) -> list:
    lines = ["", "## Context", "", "", "## Description", "", DESCRIPTION_LABEL, "", "## Speakers", "",
             "| Label | Confirmed name |", "|---|---|"]
    for label in speakers or []:
        lines.append(f"| {label.replace('|', '/')} | not confirmed |")
    lines += ["", "## Uncertain passages", ""]
    lines += [f"- {loc} — {why}" for loc, why in uncertain]
    if uncertain:
        lines.append("")
    lines += ["## Extracted content", "", CONTENT_START]
    if content:
        lines += content.split("\n")
    lines += [CONTENT_END, ""]
    return lines


def render_source(fields: dict, speakers, uncertain: list, content: str) -> str:
    return "\n".join(render_front_matter(fields) + render_body(speakers, uncertain, content))


def with_fields(src: Source, updates: dict) -> str:
    """The source's text with its front matter re-rendered from its fields plus `updates`."""
    if not src.fm_ok or src.fm_errors:
        raise Fail(EXIT_USAGE, {"error": "front-matter-unreadable", "id": src.id,
                                "detail": "Fix the source's front matter first; nothing was written."})
    fields = dict(src.fields)
    fields.update(updates)
    return "\n".join(render_front_matter(fields) + src.lines[src.body_start:])


def source_from_text(path: Path, rel: str, text: str) -> Source:
    return Source(path, rel, text)


# --- The index ------------------------------------------------------------------------------


def index_row(src: Source) -> str:
    title = src.f("title").replace("|", "\\|")
    when = src.f("meeting_date") if src.is_meeting and src.f("meeting_date") else src.f("source_date")
    restricted = "yes" if src.restricted else "no"
    return (f"| {src.id} | {title} | {src.f('material')} | {when} | {src.f('origin')} | "
            f"{src.f('status')} | {restricted} |")


def index_rows(text: str) -> dict:
    rows = {}
    for i, line in enumerate(text.split("\n")):
        m = re.match(r"^\|\s*(S-\d{3,})\s*\|", line)
        if m:
            rows.setdefault(m.group(1), (i + 1, line.rstrip()))
    return rows


def upsert_index(text: str, rows: dict) -> str:
    """Insert or replace `rows` (ID → row) in the index table, keeping ID order."""
    lines = text.split("\n")
    header = next((i for i, l in enumerate(lines) if re.match(r"^\|\s*ID\s*\|", l)), None)
    if header is None:
        if lines and lines[-1] == "":
            lines.pop()
        lines += ["", "| ID | Title | Type | Date | Origin | Status | Restricted |", "|---|---|---|---|---|---|---|"]
        header = len(lines) - 2
        lines.append("")
    start = header + 2 if header + 1 < len(lines) and TABLE_SEPARATOR.match(lines[header + 1]) else header + 1
    end = start
    while end < len(lines) and lines[end].strip().startswith("|"):
        end += 1
    existing = {}
    others = []
    for line in lines[start:end]:
        m = re.match(r"^\|\s*(S-\d{3,})\s*\|", line)
        if m:
            existing[m.group(1)] = line
        else:
            others.append(line)
    existing.update(rows)
    ordered = [existing[k] for k in sorted(existing, key=lambda s: int(s[2:]))]
    return "\n".join(lines[:start] + others + ordered + lines[end:])


# --- The engagement -------------------------------------------------------------------------


def _walk_roots() -> list:
    return [f for f in CONTENT_FOLDERS if f.rpartition("/")[0] not in CONTENT_FOLDERS]


def raw_format(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    return FORMATS.get(ext, ext.lstrip(".") or "none")


def supported(fmt: str) -> bool:
    return fmt in FORMATS.values()


_VERSION_SUFFIX = re.compile(
    r"([\s._-]*\(\d+\)|[\s._-]*v\d+|[\s._-]*(final|draft|copy)|[\s._-]*rev[\s._-]*\d+"
    r"|[\s._-]*\d{4}-\d{2}-\d{2}|[\s._-]*\d{8})$"
)


def version_stem(name: str) -> str:
    """The file name stem, lower-cased, with version suffixes stripped (v2, final, draft, rev 3, dates, (1))."""
    stem = os.path.splitext(os.path.basename(name))[0].lower().strip()
    stem = re.sub(r"^copy[\s._-]+of[\s._-]+", "", stem)
    while True:
        new = _VERSION_SUFFIX.sub("", stem).strip(" ._-")
        if new == stem or not new:
            return stem
        stem = new


class Engagement:
    def __init__(self, root: Path):
        self.root = root
        text = read_text(root / "engagement.md")
        lines = (text or "").splitlines()
        fm_lines, _ = split_front_matter(lines)
        if text is None or fm_lines is None:
            raise Fail(EXIT_NO_ENGAGEMENT, {"error": "engagement-unreadable",
                                            "detail": "The engagement record (engagement.md) could not be read."})
        self.record, _ = parse_mapping(fm_lines, 2)
        # The real client name is kept here only, for the leak check and output redaction.
        self._client = _str(self.record.get("client")).strip()
        self.code_name = _str(self.record.get("client_code_name")).strip()
        self.raw = root / RAW_DIR
        self.extracted = root / EXTRACTED_DIR
        self._sources = None

    @property
    def uses_code_name(self) -> bool:
        return bool(self.code_name)

    @property
    def policy(self) -> str:
        value = _str(self.record.get("model_use")).strip()
        return value if value in ("allowed", "restricted") else "unconfirmed"

    def engagement_block(self) -> dict:
        return {
            "root": str(self.root),
            "id": _str(self.record.get("id")),
            "engagement_name": _str(self.record.get("engagement_name")),
            "client_label": self.code_name or self._client,
            "uses_code_name": self.uses_code_name,
            "lead_consultant": _str(self.record.get("lead_consultant")),
            "framework_version": _str(self.record.get("framework_version")),
            "model_use": _str(self.record.get("model_use")),
            "model_use_notes": _str(self.record.get("model_use_notes")),
        }

    def redact(self, obj):
        """Remove the real client name from anything printed, when a code name is in use."""
        if not (self.uses_code_name and self._client):
            return obj
        pattern = re.compile(re.escape(self._client), re.IGNORECASE)

        def walk(o):
            if isinstance(o, str):
                return pattern.sub("[redacted]", o)
            if isinstance(o, list):
                return [walk(v) for v in o]
            if isinstance(o, dict):
                return {k: walk(v) for k, v in o.items()}
            return o

        return walk(obj)

    # sources

    def sources(self) -> list:
        if self._sources is None:
            result = []
            if self.extracted.is_dir():
                for path in sorted(self.extracted.glob("*.md")):
                    text = read_text(path)
                    if text is not None:
                        result.append(Source(path, path.relative_to(self.root).as_posix(), text))
            self._sources = result
        return self._sources

    def reload(self) -> None:
        self._sources = None

    def source(self, id_: str) -> Source:
        if not SOURCE_ID.match(id_ or ""):
            raise Fail(EXIT_USAGE, {"error": "bad-id", "detail": f"not a source ID: {id_!r} (expected for example S-003)"})
        for src in self.sources():
            if src.id == id_:
                return src
        raise Fail(EXIT_USAGE, {"error": "unknown-id", "id": id_})

    def by_raw(self, rel: str) -> list:
        return [s for s in self.sources() if s.f("raw_file") == rel]

    def restricted_raws(self) -> set:
        return {s.f("raw_file") for s in self.sources() if s.restricted}

    # paths

    def resolve_raw(self, arg: str):
        """(relative path inside raw/, absolute path) or raise exit 5 `outside-raw`."""
        raw_root = self.raw.resolve()
        candidates = []
        p = Path(arg)
        if p.is_absolute():
            candidates.append(p)
        else:
            candidates += [self.raw / p, self.root / p, Path(os.getcwd()) / p]
        for cand in candidates:
            if os.path.lexists(str(cand)):
                resolved = cand.resolve()
                try:
                    rel = resolved.relative_to(raw_root).as_posix()
                except ValueError:
                    raise Fail(EXIT_CANT_EXTRACT, {"reason": "outside-raw", "raw": arg,
                                                   "detail": "Copy the file into 10-sources/raw/ first."})
                return rel, resolved
        raise Fail(EXIT_USAGE, {"error": "not-found", "raw": arg})

    def raw_files(self) -> list:
        result = []
        if not self.raw.is_dir():
            return result
        for dirpath, dirnames, filenames in os.walk(self.raw):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for name in sorted(filenames):
                if name.startswith("."):
                    continue
                path = Path(dirpath) / name
                rel = path.relative_to(self.raw).as_posix()
                try:
                    size = os.stat(str(path)).st_size
                except OSError:
                    size = 0
                result.append((rel, size))
        return result

    # numbering (R16)

    def scan_texts(self) -> dict:
        """Every `*.md` under the content folders outside 10-sources/ (never raw/)."""
        texts = {}
        for top in _walk_roots():
            base = self.root / top
            if not base.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
                for name in sorted(filenames):
                    if name.endswith(".md"):
                        path = Path(dirpath) / name
                        text = read_text(path)
                        if text is not None:
                            texts[path.relative_to(self.root).as_posix()] = text
        return texts

    def highest_source_number(self) -> int:
        highest = 0
        for src in self.sources():
            m = re.match(r"^S-(\d{3,})$", src.stem)
            if m:
                highest = max(highest, int(m.group(1)))
            for _, _, line in src.outside_content():
                for m in S_MENTION.finditer(line):
                    highest = max(highest, int(m.group(1)))
        index = read_text(self.root / INDEX) or ""
        for m in S_MENTION.finditer(index):
            highest = max(highest, int(m.group(1)))
        for text in self.scan_texts().values():
            for m in S_MENTION.finditer(text):
                highest = max(highest, int(m.group(1)))
        return highest

    def next_id(self) -> str:
        return f"S-{self.highest_source_number() + 1:03d}"

    def id_problems(self) -> list:
        problems = []
        seen = {}
        for src in self.sources():
            field_id = src.f("id")
            if src.fm_ok is False or src.fm_errors:
                problems.append(_p("unparseable", src.id, src.rel, None, "front matter could not be read"))
            if not SOURCE_ID.match(src.stem):
                problems.append(_p("malformed-id", src.id, src.rel, None, "file name must be `S-<3+ digits>.md`"))
            elif field_id and field_id != src.stem:
                problems.append(_p("malformed-id", src.id, src.rel, 2, f"file name differs from id field {field_id!r}"))
            elif field_id and not SOURCE_ID.match(field_id):
                problems.append(_p("malformed-id", src.id, src.rel, 2, f"id {field_id!r} is not `S-<3+ digits>`"))
            if field_id:
                if field_id in seen:
                    problems.append(_p("duplicate-id", field_id, src.rel, 2, f"also in {seen[field_id]}"))
                else:
                    seen[field_id] = src.rel
        return problems


def _p(code, id_, file, line, detail, locator=None) -> dict:
    out = {"code": code, "id": id_, "file": file}
    if locator is not None:
        out["locator"] = locator
    out["line"] = line
    out["detail"] = detail
    return out


# --- Access to originals (R6) ---------------------------------------------------------------


def guard_original(eng: Engagement, rel: str) -> Path:
    """Refuse (exit 3) unless the policy allows opening `rel` and no source of it is restricted."""
    if eng.policy == "unconfirmed":
        raise Fail(EXIT_POLICY, {"refused": "policy-unconfirmed",
                                 "detail": "Settle model use with charter first. No file was opened."})
    for src in eng.by_raw(rel):
        if src.restricted:
            raise Fail(EXIT_POLICY, {"refused": "restricted-source", "restricted_source": src.id,
                                     "detail": "This file is registered as restricted. No file was opened."})
    return eng.raw / rel


def open_original(eng: Engagement, rel: str) -> bytes:
    global RAW_READS
    path = guard_original(eng, rel)
    RAW_READS += 1
    with open(str(path), "rb") as fh:
        return fh.read()


def run_tool(eng: Engagement, rel: str, args: list) -> subprocess.CompletedProcess:
    """Run a poppler tool on an original (after the guard), with an argument list and a timeout."""
    global RAW_READS
    path = guard_original(eng, rel)
    RAW_READS += 1
    argv = [str(path) if a == "{}" else a for a in args]
    if "{}" not in args:
        argv.append(str(path))
    try:
        return subprocess.run(argv, capture_output=True, timeout=TOOL_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(EXIT_CANT_EXTRACT, {"reason": "unreadable", "raw": rel, "detail": f"{args[0]} failed"})


def poppler_available() -> bool:
    return all(shutil.which(t) for t in POPPLER)


def unreadable(rel: str, detail: str):
    return Fail(EXIT_CANT_EXTRACT, {"reason": "unreadable", "raw": rel, "detail": detail})


# --- Extraction results ---------------------------------------------------------------------


class Extraction:
    def __init__(self, content: str = "", uncertain=None, speakers=None, fields=None,
                 material: str = "document", block_name=None, block=None, next_step: str = "",
                 images=None):
        self.content = content
        self.uncertain = uncertain or []  # [(locator, why)]
        self.speakers = speakers  # list of labels for transcripts, else None
        self.fields = fields or {}
        self.material = material
        self.block_name = block_name
        self.block = block
        self.next = next_step
        self.images = images or []  # [(file name, bytes)] for the work folder


# --- PDF (R4) ---------------------------------------------------------------------------------


def _roman(n: int) -> str:
    out = ""
    for value, sym in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
                       (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= value:
            out += sym
            n -= value
    return out


def _letters(n: int) -> str:
    return chr(ord("a") + (n - 1) % 26) * ((n - 1) // 26 + 1)


def _pdf_object(data: bytes, num: int, gen: int):
    m = re.search(rb"(?<!\d)%d\s+%d\s+obj\b(.*?)endobj" % (num, gen), data, re.S)
    return m.group(1) if m else None


def pdf_page_labels(data: bytes, count: int) -> list:
    """Best-effort `/PageLabels` reader for uncompressed PDFs; None for each page it can't label."""
    labels = [None] * count
    try:
        m = re.search(rb"/PageLabels\s*(?:(\d+)\s+(\d+)\s+R|(<<))", data)
        if not m:
            return labels
        if m.group(1):
            tree = _pdf_object(data, int(m.group(1)), int(m.group(2))) or b""
        else:
            tree = data[m.start(3):m.start(3) + 4000]
        nums = re.search(rb"/Nums\s*\[(.*?)\]\s*>>", tree, re.S)
        if not nums:
            return labels
        ranges = []
        for item in re.finditer(rb"(\d+)\s*(<<.*?>>|\d+\s+\d+\s+R)", nums.group(1), re.S):
            start, body = int(item.group(1)), item.group(2)
            ref = re.match(rb"(\d+)\s+(\d+)\s+R", body)
            if ref:
                body = _pdf_object(data, int(ref.group(1)), int(ref.group(2))) or b""
            style = re.search(rb"/S\s*/(\w)", body)
            st = re.search(rb"/St\s+(\d+)", body)
            prefix = re.search(rb"/P\s*\((.*?)\)", body)
            ranges.append((start, style.group(1).decode() if style else "",
                           int(st.group(1)) if st else 1, prefix.group(1).decode("latin-1") if prefix else ""))
        ranges.sort()
        for page in range(count):
            current = [r for r in ranges if r[0] <= page]
            if not current:
                continue
            start, style, first, prefix = current[-1]
            n = first + page - start
            number = {"D": str(n), "r": _roman(n), "R": _roman(n).upper(), "a": _letters(n),
                      "A": _letters(n).upper()}.get(style, "")
            labels[page] = prefix + number
    except (ValueError, re.error):
        return [None] * count
    return labels


def pdf_check_bytes(data: bytes, rel: str) -> None:
    if not data.lstrip()[:5] == b"%PDF-":
        raise unreadable(rel, "not a PDF (no %PDF- header)")
    if re.search(rb"/Encrypt\s*(?:\d+\s+\d+\s+R|<<)", data):
        raise unreadable(rel, "encrypted PDF")


def pdf_estimate_pages(data: bytes) -> int:
    """Page objects, or the page tree's /Count when the page objects are compressed; 0 if unknown."""
    objects = len(re.findall(rb"/Type\s*/Page(?![s\w])", data))
    counts = [int(m.group(1)) for d in re.finditer(rb"<<[^<>]*?/Type\s*/Pages\b[^<>]*>>", data)
              for m in [re.search(rb"/Count\s+(\d+)", d.group(0))] if m]
    return max([objects] + counts)


# Without poppler, Claude Code's Read can only open a PDF whole, and it needs a page range
# above this many pages (research R4, checked during implementation).
UNCHECKED_MAX_PAGES = 10


def pdf_info(eng: Engagement, rel: str) -> dict:
    result = run_tool(eng, rel, ["pdfinfo"])
    if result.returncode != 0:
        raise unreadable(rel, "pdfinfo could not read the file (damaged or encrypted)")
    info = {}
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        key, _, value = line.partition(":")
        info[key.strip()] = value.strip()
    if info.get("Encrypted", "no").lower().startswith("yes"):
        raise unreadable(rel, "encrypted PDF")
    pages = _int(info.get("Pages", ""))
    if not pages:
        raise unreadable(rel, "the PDF has no pages")
    return {"pages": pages}


def pdf_text_pages(eng: Engagement, rel: str, count: int) -> list:
    result = run_tool(eng, rel, ["pdftotext", "-enc", "UTF-8", "{}", "-"])
    if result.returncode != 0:
        raise unreadable(rel, "pdftotext could not read the file")
    text = result.stdout.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
    parts = text.split("\f")
    pages = [p.strip("\n") for p in parts[:count]]
    while len(pages) < count:
        pages.append("")
    return [p.rstrip() for p in pages]


def pdf_image_pages(eng: Engagement, rel: str) -> dict:
    result = run_tool(eng, rel, ["pdfimages", "-list"])
    counts: dict = {}
    if result.returncode != 0:
        return counts
    for line in result.stdout.decode("utf-8", "replace").splitlines()[2:]:
        parts = line.split()
        if parts and parts[0].isdigit():
            counts[int(parts[0])] = counts.get(int(parts[0]), 0) + 1
    return counts


def render_pdf(pages: list, labels: list) -> str:
    out = []
    for n, text in enumerate(pages, start=1):
        label = labels[n - 1] if n - 1 < len(labels) else None
        marker = f"### p. {n}" + (f" (printed: {label})" if label and label != str(n) else "")
        out.append(marker)
        out.append("")
        if text.strip():
            out += text.split("\n")
            out.append("")
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def extract_pdf(eng: Engagement, ctx: dict) -> Extraction:
    data, rel = ctx["data"], ctx["rel"]
    pdf_check_bytes(data, rel)
    if not poppler_available():
        estimate = pdf_estimate_pages(data)
        if estimate > UNCHECKED_MAX_PAGES:
            raise Fail(EXIT_CANT_EXTRACT, {
                "reason": "needs-poppler", "raw": rel, "page_count_estimate": estimate,
                "install_hint": INSTALL_HINT,
                "detail": f"Without poppler only PDFs of up to {UNCHECKED_MAX_PAGES} pages can be read. "
                          "Nothing was written."})
        return Extraction(
            content="", fields={"fidelity": "unchecked", "page_count": 0, "pages_reviewed": 0},
            block_name="pdf", block={"mode": "unchecked", "page_count_estimate": estimate, "pages_reviewed": 0},
            next_step=("poppler is not installed: view the PDF with Read (at most 20 pages per call) and copy "
                       "each page's text-layer text under a `### p. n` marker exactly as it appears; set "
                       "page_count from Read; add the same table, OCR and description callouts as in checked "
                       "mode; update pages_reviewed after each batch; run verify"),
        )
    count = pdf_info(eng, rel)["pages"]
    pages = pdf_text_pages(eng, rel, count)
    images = pdf_image_pages(eng, rel)
    labels = pdf_page_labels(data, count)
    page_info, low, uncertain = [], [], []
    for n, text in enumerate(pages, start=1):
        chars = len(text.strip())
        page_info.append({"page": n, "chars": chars, "label": labels[n - 1] or str(n), "images": images.get(n, 0)})
        if chars < 40:
            low.append(n)
        if chars == 0:
            uncertain.append((f"p. {n}", "no text layer"))
    return Extraction(
        content=render_pdf(pages, labels), uncertain=uncertain,
        fields={"fidelity": "pending", "page_count": count, "pages_reviewed": 0},
        block_name="pdf",
        block={"page_count": count, "pages_reviewed": 0, "pages": page_info, "low_text_pages": low,
               "image_pages": sorted(n for n in images if images[n]),
               "label_differs": [p["page"] for p in page_info if p["label"] != str(p["page"])]},
        next_step=f"view pages 1–{min(20, count)} with Read, then edit the file; run verify",
    )


def expected_pdf(eng: Engagement, src: Source):
    rel = src.f("raw_file")
    count = src.i("page_count") or 0
    if count <= 0:
        return None
    data = open_original(eng, rel)
    return render_pdf(pdf_text_pages(eng, rel, count), pdf_page_labels(data, count))


# --- Word (R5) --------------------------------------------------------------------------------

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "v": "urn:schemas-microsoft-com:vml",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _q(tag: str) -> str:
    prefix, _, local = tag.partition(":")
    return "{%s}%s" % (NS[prefix], local)


W = lambda local: _q("w:" + local)  # noqa: E731
VIEWABLE = (".png", ".jpg", ".jpeg", ".gif", ".webp")
MAX_DOCX_BYTES = 500 * 1024 * 1024


class DocxReader:
    def __init__(self, data: bytes, rel: str, source_id: str, keep_images: bool):
        self.rel, self.source_id, self.keep_images = rel, source_id, keep_images
        if data[:8] == bytes.fromhex("D0CF11E0A1B11AE1"):
            raise unreadable(rel, "password-protected or legacy Word file")
        try:
            import io

            self.zip = zipfile.ZipFile(io.BytesIO(data))
            if sum(i.file_size for i in self.zip.infolist()) > MAX_DOCX_BYTES:
                raise unreadable(rel, "the document is too large to unpack")
            self.document = self._xml("word/document.xml")
        except (zipfile.BadZipFile, KeyError, ET.ParseError, ValueError):
            raise unreadable(rel, "not a readable .docx package")
        if self.document is None:
            raise unreadable(rel, "no word/document.xml")
        self.rels = self._rels("word/_rels/document.xml.rels")
        self.styles = self._styles()
        self.numbering = self._numbering()
        self.blocks = []  # (kind, text)
        self.path = []  # [(level, text)]
        self.seen_heading = False
        self.para_no = 0
        self.uncertain = []
        self.images = []  # (name, bytes)
        self.image_info = []
        self.counts = Counter()
        self.comment_anchor = {}
        self.list_counters = Counter()
        self.has_derived = False

    def _xml(self, name: str):
        try:
            return ET.fromstring(self.zip.read(name))
        except KeyError:
            return None

    def _rels(self, name: str) -> dict:
        root = self._xml(name)
        result = {}
        if root is None:
            return result
        for rel in root.iter(_q("pr:Relationship")):
            target = rel.get("Target", "")
            if rel.get("TargetMode") == "External":
                continue
            parts = []
            for part in ("word/" + target.lstrip("/")).split("/") if not target.startswith("/") else target.lstrip("/").split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                elif part and part != ".":
                    parts.append(part)
            result[rel.get("Id")] = "/".join(parts)
        return result

    def _styles(self) -> dict:
        root = self._xml("word/styles.xml")
        styles = {}
        if root is None:
            return styles
        for style in root.iter(W("style")):
            sid = style.get(W("styleId"))
            name = style.find(W("name"))
            based = style.find(W("basedOn"))
            styles[sid] = ((name.get(W("val")) if name is not None else sid) or "",
                           based.get(W("val")) if based is not None else None)
        return styles

    def heading_level(self, style_id):
        """0 for Title, 1–6 for headings, None otherwise (resolved through basedOn)."""
        seen = set()
        while style_id and style_id not in seen:
            seen.add(style_id)
            name, based = self.styles.get(style_id, (style_id, None))
            for candidate in (name or "", style_id):
                low = candidate.lower().replace(" ", "")
                if low == "title":
                    return 0
                m = re.match(r"^heading([1-6])$", low)
                if m:
                    return int(m.group(1))
            style_id = based
        return None

    def _numbering(self) -> dict:
        root = self._xml("word/numbering.xml")
        result = {}
        if root is None:
            return result
        abstract = {}
        for an in root.iter(W("abstractNum")):
            levels = {}
            for lvl in an.iter(W("lvl")):
                fmt = lvl.find(W("numFmt"))
                levels[lvl.get(W("ilvl"))] = fmt.get(W("val")) if fmt is not None else "bullet"
            abstract[an.get(W("abstractNumId"))] = levels
        for num in root.iter(W("num")):
            ref = num.find(W("abstractNumId"))
            if ref is not None:
                result[num.get(W("numId"))] = abstract.get(ref.get(W("val")), {})
        return result

    # locators

    def locator(self) -> str:
        if self.path:
            return "§ " + " > ".join(t for _, t in self.path)
        return f"¶ {max(self.para_no, 1)}"

    # inline content

    def inline(self, elem, deferred: list, ctx: dict) -> str:
        out = []
        for child in elem:
            tag = child.tag
            if tag == W("r"):
                out.append(self.run(child, deferred, ctx))
            elif tag in (W("ins"), W("moveTo")):
                ctx["changes"] += 1
                out.append("{++" + self.inline(child, deferred, ctx) + "++}")
            elif tag in (W("del"), W("moveFrom")):
                ctx["changes"] += 1
                out.append("{--" + self.inline(child, deferred, ctx) + "--}")
            elif tag in (W("hyperlink"), W("smartTag"), W("fldSimple"), W("customXml"), W("sdtContent")):
                out.append(self.inline(child, deferred, ctx))
            elif tag == W("sdt"):
                content = child.find(W("sdtContent"))
                if content is not None:
                    out.append(self.inline(content, deferred, ctx))
            elif tag == W("commentRangeStart"):
                self.comment_anchor.setdefault(child.get(W("id")), ctx["anchor"])
            elif tag == _q("mc:AlternateContent"):
                choice = child.find(_q("mc:Choice"))
                if choice is not None:
                    out.append(self.inline(choice, deferred, ctx))
        return "".join(out)

    def run(self, r, deferred: list, ctx: dict) -> str:
        out = []
        for child in r:
            tag = child.tag
            if tag in (W("t"), W("delText")):
                out.append(child.text or "")
            elif tag == W("tab"):
                out.append("\t")
            elif tag in (W("br"), W("cr")):
                out.append("\n")
            elif tag == W("noBreakHyphen"):
                out.append("-")
            elif tag == W("footnoteReference"):
                out.append(f"[^{child.get(W('id'))}]")
            elif tag == W("endnoteReference"):
                out.append(f"[^e{child.get(W('id'))}]")
            elif tag == W("commentReference"):
                self.comment_anchor.setdefault(child.get(W("id")), ctx["anchor"])
            elif tag in (W("drawing"), W("pict"), W("object")):
                self.drawing(child, deferred)
            elif tag == _q("mc:AlternateContent"):
                choice = child.find(_q("mc:Choice"))
                if choice is not None:
                    for grand in choice:
                        self.drawing(grand, deferred)
        return "".join(out)

    def drawing(self, elem, deferred: list) -> None:
        for txbx in elem.iter(W("txbxContent")):
            deferred.append(("textbox", txbx))
        for blip in elem.iter(_q("a:blip")):
            deferred.append(("image", blip.get(_q("r:embed")) or blip.get(_q("r:link"))))
        for img in elem.iter(_q("v:imagedata")):
            deferred.append(("image", img.get(_q("r:id"))))
        for chart in elem.iter(_q("c:chart")):
            deferred.append(("chart", chart.get(_q("r:id"))))
        for dgm in elem.iter(_q("dgm:relIds")):
            deferred.append(("diagram", dgm.get(_q("r:dm"))))

    # blocks

    def walk(self, container) -> None:
        for child in container:
            if child.tag == W("p"):
                self.paragraph(child)
            elif child.tag == W("tbl"):
                self.table(child)
            elif child.tag == W("sdt"):
                content = child.find(W("sdtContent"))
                if content is not None:
                    self.walk(content)
            elif child.tag == W("customXml"):
                self.walk(child)

    def paragraph(self, p) -> None:
        ppr = p.find(W("pPr"))
        style = None
        num = None
        if ppr is not None:
            ps = ppr.find(W("pStyle"))
            style = ps.get(W("val")) if ps is not None else None
            numpr = ppr.find(W("numPr"))
            if numpr is not None:
                nid, lvl = numpr.find(W("numId")), numpr.find(W("ilvl"))
                num = (nid.get(W("val")) if nid is not None else None, lvl.get(W("val")) if lvl is not None else "0")
        level = self.heading_level(style) if style else None
        if level == 0:
            level = 1  # Title renders as `#`; locators follow the markdown heading path
        deferred: list = []
        ctx = {"changes": 0, "anchor": None}
        # A comment anchored in a heading points at that heading's own path.
        if level is not None:
            preview = " ".join("".join(t.text or "" for t in p.iter(W("t"))).split())
            stack = [(l, t) for l, t in self.path if l < level]
            ctx["anchor"] = "§ " + " > ".join([t for _, t in stack] + [preview]) if preview else self.locator()
        else:
            ctx["anchor"] = self.locator() if self.seen_heading else f"¶ {self.para_no + 1}"
        text = self.inline(p, deferred, ctx)
        if level is not None and text.strip():
            heading = " ".join(text.split())
            self.path = [(l, t) for l, t in self.path if l < level] + [(level, heading)]
            self.seen_heading = True
            self.counts["headings"] += 1
            self.blocks.append(("block", "#" * level + " " + heading))
        elif text.strip():
            if num is not None and num[0] not in (None, "0"):
                fmt = self.numbering.get(num[0], {}).get(num[1] or "0", "bullet")
                indent = "  " * (_int(num[1] or "0") or 0)
                if fmt == "decimal":
                    self.list_counters[(num[0], num[1])] += 1
                    marker = f"{self.list_counters[(num[0], num[1])]}."
                else:
                    marker = "-"
                self.blocks.append(("list", f"{indent}{marker} " + text.replace("\n", " ")))
            else:
                body = "  \n".join(line.rstrip() for line in text.split("\n"))
                if not self.seen_heading:
                    self.para_no += 1
                    body = f"[¶{self.para_no}] " + body
                self.blocks.append(("block", body))
        if ctx["changes"]:
            self.counts["tracked_changes"] += ctx["changes"]
            for _ in range(ctx["changes"]):
                self.uncertain.append((self.locator(), "tracked change (not accepted or rejected)"))
        self.emit_deferred(deferred)

    def emit_deferred(self, deferred: list) -> None:
        for kind, value in deferred:
            if kind == "textbox":
                self.walk(value)
            elif kind == "image":
                self.image(value)
            elif kind == "chart":
                self.chart(value)
            elif kind == "diagram":
                self.diagram(value)

    def image(self, rid) -> None:
        target = self.rels.get(rid)
        if not target:
            return
        name = target.rsplit("/", 1)[-1]
        viewable = os.path.splitext(name)[1].lower() in VIEWABLE
        try:
            data = self.zip.read(target)
        except KeyError:
            return
        self.counts["images"] += 1
        if self.keep_images:
            self.images.append((name, data))
        self.image_info.append({"locator": self.locator(), "path": f"{WORK_DIR}/{self.source_id}/{name}",
                                "viewable": viewable})
        if not viewable:
            self.uncertain.append((self.locator(), "image format can't be viewed"))
        self.blocks.append(("block", f"<!-- cairn:image {name} -->"))

    def chart(self, rid) -> None:
        target = self.rels.get(rid)
        root = self._xml(target) if target else None
        if root is None:
            return
        chart = root.find(_q("c:chart"))
        title_el = chart.find(_q("c:title")) if chart is not None else None
        title = " ".join("".join(t.text or "" for t in title_el.iter(_q("a:t"))).split()) if title_el is not None else ""
        axis_el = root.find(".//" + _q("c:catAx") + "/" + _q("c:title"))
        axis = " ".join("".join(t.text or "" for t in axis_el.iter(_q("a:t"))).split()) if axis_el is not None else ""
        series = []
        categories = []
        for n, ser in enumerate(root.iter(_q("c:ser")), start=1):
            tx = ser.find(_q("c:tx"))
            name = " ".join(v.text or "" for v in tx.iter(_q("c:v"))).strip() if tx is not None else ""
            cat = ser.find(_q("c:cat"))
            val = ser.find(_q("c:val"))

            def points(el):
                pts = {}
                if el is None:
                    return pts
                for pt in el.iter(_q("c:pt")):
                    v = pt.find(_q("c:v"))
                    pts[_int(pt.get("idx") or "0") or 0] = (v.text or "").strip() if v is not None else ""
                return pts

            cats, vals = points(cat), points(val)
            if not categories and cats:
                categories = [cats[k] for k in sorted(cats)]
            series.append((name or f"Series {n}", vals))
        rows = max([len(categories)] + [max(v) + 1 if v else 0 for _, v in series])
        if not categories:
            categories = [str(i + 1) for i in range(rows)]
        lines = ["> [!derived] chart-data", f"> **Chart:** {title}".rstrip()]
        header = [axis or "Category"] + [name for name, _ in series]
        lines.append("> | " + " | ".join(h.replace("|", "\\|") for h in header) + " |")
        lines.append("> |" + "---|" * len(header))
        for i in range(rows):
            cells = [categories[i] if i < len(categories) else ""] + [v.get(i, "") for _, v in series]
            lines.append("> | " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
        self.counts["charts"] += 1
        self.has_derived = True
        self.blocks.append(("block", "\n".join(lines)))

    def diagram(self, rid) -> None:
        target = self.rels.get(rid)
        root = self._xml(target) if target else None
        if root is None:
            return
        items = []
        for pt in root.iter(_q("dgm:pt")):
            t = pt.find(_q("dgm:t"))
            if t is None:
                continue
            text = " ".join("".join(a.text or "" for a in t.iter(_q("a:t"))).split())
            if text:
                items.append(text)
        if not items:
            return
        self.has_derived = True
        self.blocks.append(("block", "\n".join(["> [!derived] diagram-text"] + [f"> - {i}" for i in items])))

    def cell_text(self, tc, deferred: list, ctx: dict, flags: dict) -> str:
        parts = []
        for child in tc:
            if child.tag == W("p"):
                parts.append(self.inline(child, deferred, ctx))
            elif child.tag == W("tbl"):
                flags["nested"] = True
                for inner in child.iter(W("tc")):
                    parts.append(self.cell_text(inner, deferred, ctx, flags))
            elif child.tag == W("sdt"):
                content = child.find(W("sdtContent"))
                if content is not None:
                    parts.append(self.cell_text(content, deferred, ctx, flags))
        text = " ".join(" ".join(p.split()) for p in parts if p.strip())
        return text.replace("|", "\\|")

    def table(self, tbl) -> None:
        rows = []
        above: dict = {}
        flags = {"merged": False, "nested": False}
        deferred: list = []
        ctx = {"changes": 0, "anchor": self.locator()}
        for tr in tbl.findall(W("tr")):
            row, col = [], 0
            for tc in tr.findall(W("tc")):
                tcpr = tc.find(W("tcPr"))
                span = 1
                vmerge = None
                if tcpr is not None:
                    gs = tcpr.find(W("gridSpan"))
                    span = _int(gs.get(W("val")) or "1") or 1 if gs is not None else 1
                    vm = tcpr.find(W("vMerge"))
                    if vm is not None:
                        vmerge = vm.get(W("val")) or "continue"
                text = self.cell_text(tc, deferred, ctx, flags)
                if vmerge == "continue":
                    text = above.get(col, "")
                    flags["merged"] = True
                elif vmerge == "restart":
                    above[col] = text
                else:
                    above.pop(col, None)
                if span > 1:
                    flags["merged"] = True
                row += [text] * span
                col += span
            rows.append(row)
        if not rows:
            return
        width = max(len(r) for r in rows)
        lines = []
        for n, row in enumerate(rows):
            row = row + [""] * (width - len(row))
            lines.append("| " + " | ".join(row) + " |")
            if n == 0:
                lines.append("|" + "---|" * width)
        self.counts["tables"] += 1
        self.blocks.append(("block", "\n".join(lines)))
        if flags["merged"]:
            self.uncertain.append((self.locator(), "merged cells in table"))
        if flags["nested"]:
            self.uncertain.append((self.locator(), "nested table flattened into its cell"))
        if ctx["changes"]:
            self.counts["tracked_changes"] += ctx["changes"]
            for _ in range(ctx["changes"]):
                self.uncertain.append((self.locator(), "tracked change (not accepted or rejected)"))
        self.emit_deferred(deferred)

    def notes(self) -> None:
        notes = []
        for part, prefix, tag in (("footnotes", "", "footnote"), ("endnotes", "e", "endnote")):
            target = next((t for t in self.rels.values() if t == f"word/{part}.xml"), None)
            root = self._xml(target) if target else None
            if root is None:
                continue
            for note in root.iter(W(tag)):
                if note.get(W("type")) in ("separator", "continuationSeparator", "continuationNotice"):
                    continue
                ctx = {"changes": 0, "anchor": None}
                text = " ".join(" ".join(self.inline(p, [], ctx).split()) for p in note.iter(W("p")))
                if text.strip():
                    notes.append(f"[^{prefix}{note.get(W('id'))}]: {text.strip()}")
                    self.counts["footnotes"] += 1
        if notes:
            self.blocks.append(("block", "<!-- cairn:footnotes -->"))
            for note in notes:
                self.blocks.append(("block", note))

    def comments(self) -> None:
        target = next((t for t in self.rels.values() if t == "word/comments.xml"), None)
        root = self._xml(target) if target else None
        if root is None:
            return
        items = []
        for n, comment in enumerate(root.iter(W("comment")), start=1):
            author = " ".join((comment.get(W("author")) or "unknown").split())
            when = (comment.get(W("date")) or "")[:10]
            anchor = self.comment_anchor.get(comment.get(W("id"))) or "(not anchored)"
            ctx = {"changes": 0, "anchor": None}
            texts = [" ".join(self.inline(p, [], ctx).split()) for p in comment.iter(W("p"))]
            lines = [f"> [!comment] {n} · {author} · {when} · {anchor}"] + [f"> {t}" for t in texts if t]
            items.append("\n".join(lines))
        if items:
            self.counts["comments"] += len(items)
            self.blocks.append(("block", "<!-- cairn:comments -->"))
            for item in items:
                self.blocks.append(("block", item))

    def read(self) -> Extraction:
        body = self.document.find(W("body"))
        if body is None:
            raise unreadable(self.rel, "the document has no body")
        self.walk(body)
        words = sum(len(t.split()) for k, t in self.blocks)
        if not words:
            raise unreadable(self.rel, "the document is empty")
        self.notes()
        self.comments()
        out = []
        for n, (kind, text) in enumerate(self.blocks):
            if n and not (kind == "list" and self.blocks[n - 1][0] == "list"):
                out.append("")
            out.append(text)
        return Extraction(
            content="\n".join(out), uncertain=self.uncertain,
            fields={"fidelity": "pending", "extraction_method": "mixed" if self.has_derived else "text",
                    "derived": self.has_derived},
            block_name="docx",
            block={"headings": self.counts["headings"], "tables": self.counts["tables"],
                   "images": self.image_info, "charts": self.counts["charts"],
                   "comments": self.counts["comments"], "tracked_changes": self.counts["tracked_changes"],
                   "footnotes": self.counts["footnotes"]},
            next_step=("read the source; view each viewable image in the work folder and add a "
                       "vision-description callout under its placeholder; add a Description line under "
                       "each chart-data table; run verify"),
            images=self.images,
        )


def extract_docx(eng: Engagement, ctx: dict) -> Extraction:
    return DocxReader(ctx["data"], ctx["rel"], ctx["id"], keep_images=True).read()


# --- Text, markdown and transcripts (R9, R10) -------------------------------------------------


def decode_text(data: bytes, rel: str) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        try:
            text = data[3:].decode("utf-8")
        except UnicodeDecodeError:
            raise unreadable(rel, "unknown text encoding (not UTF-8 or cp1252)")
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("cp1252")
            except UnicodeDecodeError:
                raise unreadable(rel, "unknown text encoding (not UTF-8 or cp1252)")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise unreadable(rel, "the file is empty")
    return text


def _ts(raw: str) -> str:
    parts = raw.split(":")
    parts[-1] = re.split(r"[.,]", parts[-1])[0]
    nums = [int(p) for p in parts]
    while len(nums) < 3:
        nums.insert(0, 0)
    return "%02d:%02d:%02d" % tuple(nums[-3:])


TIME = r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?"
INLINE_SHAPES = (
    ("bracket-time", re.compile(rf"^\[({TIME})\]\s*(?:\*\*)?([^:*\]\[]{{1,40}}?)(?:\*\*)?:\s*(.*)$")),
    ("bold-name", re.compile(r"^\*\*([^*:\n]{1,40}?):?\*\*:?\s+(.*)$")),
)
LINE_SHAPES = (
    ("name-time-line", re.compile(rf"^([^\s\d:\[*][^:\n]{{0,39}}?)\s{{2,}}({TIME})\s*$")),
    ("name-paren-time", re.compile(rf"^([^\s()\[*][^()\n]{{0,39}}?)\s*\(({TIME})\)\s*:?\s*(.*)$")),
)
NAME_COLON = re.compile(r"^([A-Z][^:\n*\[\]]{0,39}?):\s+(\S.*)$")


def _parse_shape(shape: str, lines: list):
    """Turns as [label, timestamp or None, [text parts]], plus the number of lines covered."""
    turns, covered, headers = [], 0, 0
    own_line = shape in ("name-time-line", "name-paren-time")
    regex = dict(INLINE_SHAPES + LINE_SHAPES).get(shape, NAME_COLON)
    for line in lines:
        s = line.strip()
        if not s:
            continue
        m = regex.match(s)
        if m:
            headers += 1
            covered += 1
            if shape == "bracket-time":
                ts, label, text = m.group(1), m.group(2), m.group(3)
            elif shape == "name-time-line":
                label, ts, text = m.group(1), m.group(2), ""
            elif shape == "name-paren-time":
                label, ts, text = m.group(1), m.group(2), m.group(3)
            else:
                label, ts, text = m.group(1), None, m.group(2)
            turns.append([" ".join(label.split()), _ts(ts) if ts else None, [text.strip()] if text.strip() else []])
            continue
        if turns:
            turns[-1][2].append(s)
            if own_line:
                covered += 1
        else:
            turns.append(["(unlabelled)", None, [s]])
    return turns, covered, headers


def detect_transcript(text: str):
    lines = text.split("\n")
    nonblank = sum(1 for l in lines if l.strip())
    if not nonblank:
        return None
    for shape in ("bracket-time", "bold-name", "name-time-line", "name-paren-time", "name-colon"):
        turns, covered, headers = _parse_shape(shape, lines)
        if headers >= 2 and covered / nonblank >= 0.6:
            return shape, turns
    return None


VOICE = re.compile(r"^<v(?:\.[^\s>]*)?\s+([^>]+)>")
PREFIX = re.compile(r"^([^:<>\n]{1,40}):\s+(.*)$")


def _cues(text: str, fmt: str) -> list:
    """[(timestamp, [text lines])] for VTT or SRT."""
    cues = []
    for block in re.split(r"\n\s*\n", text.strip("\n")):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        if fmt == "vtt" and lines[0].strip().startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        at = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if at is None:
            continue
        start = lines[at].split("-->")[0].strip()
        if not re.match(rf"^{TIME}$", start):
            continue
        cues.append((_ts(start), lines[at + 1 :]))
    return cues


def parse_captions(text: str, fmt: str):
    cues = _cues(text, fmt)
    voiced = any(lines and VOICE.match(lines[0].strip()) for _, lines in cues)
    prefixed = sum(1 for _, lines in cues if lines and PREFIX.match(lines[0].strip()))
    if fmt == "vtt" and voiced:
        shape = "vtt-voice"
    elif cues and prefixed / len(cues) >= 0.6:
        shape = "vtt-prefix" if fmt == "vtt" else "srt-prefix"
    else:
        shape = "unlabelled"
    turns = []
    for ts, lines in cues:
        label = "(unlabelled)"
        parts = [l.strip() for l in lines]
        if parts and shape == "vtt-voice":
            m = VOICE.match(parts[0])
            if m:
                label = " ".join(m.group(1).split())
                parts[0] = parts[0][m.end():]
        elif parts and shape in ("vtt-prefix", "srt-prefix"):
            m = PREFIX.match(parts[0])
            if m:
                label, parts[0] = " ".join(m.group(1).split()), m.group(2)
        parts = [p.replace("</v>", "").strip() for p in parts]
        turns.append([label, ts, [p for p in parts if p]])
    return shape, turns


def merge_turns(turns: list) -> list:
    merged = []
    for label, ts, parts in turns:
        if merged and label == merged[-1][0] and label != "(unlabelled)":
            merged[-1][2].extend(parts)
        else:
            merged.append([label, ts, list(parts)])
    return merged


def render_turns(turns: list) -> tuple:
    out, labels = [], []
    for n, (label, ts, parts) in enumerate(turns, start=1):
        if label not in labels:
            labels.append(label)
        stamp = f"T{n} · {ts}" if ts else f"T{n}"
        text = " ".join(parts)
        out.append(f"**{label}** [{stamp}]: {text}".rstrip())
        out.append("")
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out), labels


def transcript_extraction(shape: str, turns: list) -> Extraction:
    turns = merge_turns(turns)
    content, labels = render_turns(turns)
    generic = [l for l in labels if GENERIC_LABEL.match(l)]
    return Extraction(
        content=content, speakers=labels, material="meeting-transcript",
        fields={"fidelity": "pending"},
        block_name="transcript",
        block={"shape": shape, "turns": len(turns), "timestamps": any(t[1] for t in turns),
               "labels": labels, "generic_labels": generic},
        next_step=("ask the consultant who each generic label is and record confirmed names in "
                   "## Speakers only; fill the metadata; run verify"),
    )


def number_paragraphs(text: str) -> str:
    """Plain text: `[¶n]` per blank-line block, line breaks kept as two-space hard breaks."""
    out, n = [], 0
    for block in re.split(r"\n[ \t]*\n", text.strip("\n")):
        lines = [l.rstrip() for l in block.split("\n")]
        if not any(l.strip() for l in lines):
            continue
        n += 1
        out.append(f"[¶{n}] " + "  \n".join(lines))
    return "\n\n".join(out)


def markdown_document(text: str) -> str:
    """Markdown copied as is; paragraphs before the first heading get `[¶n]` prefixes."""
    lines = text.rstrip("\n").split("\n")
    first_heading = next((i for i, l in enumerate(lines) if HEADING.match(l)), len(lines))
    head = "\n".join(lines[:first_heading])
    out = []
    n = 0
    if head.strip():
        for block in re.split(r"\n[ \t]*\n", head.strip("\n")):
            if block.strip():
                n += 1
                out.append(f"[¶{n}] " + block)
    rest = "\n".join(lines[first_heading:])
    return "\n\n".join(out + ([rest] if rest else []))


def extract_textlike(eng: Engagement, ctx: dict) -> Extraction:
    rel, fmt, mode = ctx["rel"], ctx["format"], ctx.get("as")
    text = decode_text(ctx["data"], rel)
    if fmt in ("vtt", "srt"):
        shape, turns = parse_captions(text, fmt)
        if not turns:
            raise unreadable(rel, "no captions found")
        ext = transcript_extraction(shape, turns)
        if shape == "unlabelled":
            ext.next = ("the captions have no speaker labels: ask the consultant whether the speakers can be "
                        "identified; fill the metadata; run verify")
        return ext
    if mode != "document":
        found = detect_transcript(text)
        if found:
            return transcript_extraction(*found)
        if mode == "transcript":
            raise Fail(EXIT_CANT_EXTRACT, {"reason": "transcript-format-unknown", "raw": rel,
                                           "detail": "No known transcript shape matched. Nothing was written."})
    content = markdown_document(text) if fmt == "markdown" else number_paragraphs(text)
    return Extraction(content=content, fields={"fidelity": "pending"},
                      next_step="read the source, fill the metadata and context; run verify")


EXTRACTORS = {
    "pdf": extract_pdf, "docx": extract_docx, "markdown": extract_textlike, "text": extract_textlike,
    "vtt": extract_textlike, "srt": extract_textlike,
}


# --- Fidelity comparison (R11) ----------------------------------------------------------------


def source_kind(src: Source) -> str:
    fmt = src.f("source_type")
    if fmt == "pdf":
        return "pdf"
    if fmt in ("vtt", "srt"):
        return "turns"
    if fmt in ("markdown", "text") and any(TURN_MARK.match(l) for l in src.content_lines()):
        return "turns"
    if fmt == "text":
        return "paras"
    return "doc"


def normalize(lines: list, first_line: int = 1) -> list:
    """[(1-based line, text)] with derived callouts dropped, corrected callouts replaced by their
    `was:` text, and HTML comments dropped (except the footnotes/comments unit markers)."""
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        lineno = first_line + i
        m = CALLOUT.match(line.strip())
        if m:
            kind, rest = m.group(1).lower(), m.group(2)
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith(">") and not CALLOUT.match(lines[j].strip()):
                j += 1
            if kind == "derived" or (kind == "corrected" and "derived" in rest):
                i = j
                continue
            if kind == "corrected":
                for k in range(i + 1, j):
                    body = re.sub(r"^\s*>\s?", "", lines[k])
                    if body.startswith("was:"):
                        out.append((first_line + k, body[4:].strip()))
                i = j
                continue
            out += [(first_line + k, lines[k]) for k in range(i, j)]
            i = j
            continue
        if line.strip() in UNIT_COMMENTS:
            out.append((lineno, line.strip()))
        elif HTML_COMMENT.match(line):
            pass
        else:
            out.append((lineno, line))
        i += 1
    return out


class Unit:
    def __init__(self, key, locator: str, line: int, header=None):
        self.key, self.locator, self.line, self.header = key, locator, line, header
        self.body = []


def split_units(norm: list, kind: str) -> list:
    units = [Unit("pre", "(before the first marker)", norm[0][0] if norm else 1)]
    path = []
    seen = Counter()
    for lineno, line in norm:
        s = line.rstrip()
        if kind == "pdf":
            m = PAGE_MARK.match(s)
            if m:
                units.append(Unit(int(m.group(1)), f"p. {m.group(1)}", lineno))
                continue
        elif kind == "turns":
            m = TURN_MARK.match(s)
            if m:
                ts = m.group(3)
                u = Unit(int(m.group(2)), ts or f"T{m.group(2)}", lineno, header=(m.group(1), ts))
                units.append(u)
                if m.group(4):
                    u.body.append(m.group(4))
                continue
        else:
            m = PARA_MARK.match(s)
            if m:
                u = Unit(("¶", int(m.group(1))), f"¶ {m.group(1)}", lineno)
                units.append(u)
                if m.group(2):
                    u.body.append(m.group(2))
                continue
            if kind == "doc":
                if s in UNIT_COMMENTS:
                    units.append(Unit(UNIT_COMMENTS[s], UNIT_COMMENTS[s], lineno))
                    continue
                m = HEADING.match(s)
                if m:
                    level, title = len(m.group(1)), " ".join(m.group(2).split())
                    path = [(l, t) for l, t in path if l < level] + [(level, title)]
                    locator = "§ " + " > ".join(t for _, t in path)
                    seen[locator] += 1
                    units.append(Unit((locator, seen[locator]), locator, lineno))
                    continue
        units[-1].body.append(line)
    return units


def unit_words(body: list) -> list:
    """[(word, in_table)] in order; table pipes and separator rows ignored."""
    words = []
    for line in body:
        s = line.strip()
        if s.startswith("|"):
            if TABLE_SEPARATOR.match(s):
                continue
            for cell in CELL_SPLIT.split(s.strip("|")):
                words += [(w, True) for w in cell.split()]
        else:
            words += [(w, False) for w in s.split()]
    return words


def _is_subsequence(needle: list, hay: list) -> bool:
    it = iter(hay)
    return all(any(w == h for h in it) for w in needle)


def word_diff(expected: list, actual: list) -> int:
    e_all = [w for w, _ in expected]
    a_all = [w for w, _ in actual]
    a_text = [w for w, t in actual if not t]
    ce, ca = Counter(e_all), Counter(a_all)
    if ce != ca:
        return sum(((ce - ca) + (ca - ce)).values())
    if _is_subsequence(a_text, e_all):
        return 0
    matched = sum(b.size for b in SequenceMatcher(None, e_all, a_text, autojunk=False).get_matching_blocks())
    return max(len(a_text) - matched, 1)


def compare_content(expected: str, src: Source, kind: str) -> list:
    exp_units = split_units(normalize(expected.split("\n")), kind)
    act_units = split_units(normalize(src.content_lines(), src.content_first_line()), kind)
    actual = {u.key: u for u in act_units}
    problems = []
    structural = kind in ("pdf", "turns", "paras")
    for e in exp_units:
        a = actual.pop(e.key, None)
        if a is None:
            if not structural and (e.body and any(l.strip() for l in e.body) or e.key != "pre"):
                problems.append(_p("content-mismatch", src.id, src.rel, None,
                                   "this section's heading is missing or changed", e.locator))
            continue
        if kind == "turns" and e.header != a.header:
            problems.append(_p("content-mismatch", src.id, src.rel, a.line,
                               "the speaker label or timestamp differs from the original", a.locator))
            continue
        n = word_diff(unit_words(e.body), unit_words(a.body))
        if n:
            problems.append(_p("content-mismatch", src.id, src.rel, a.line,
                               f"{n} words differ from the original", a.locator))
    for a in actual.values():
        if a.key == "pre" and not any(l.strip() for l in a.body):
            continue
        if structural and a.key != "pre":
            continue
        words = len(unit_words(a.body))
        problems.append(_p("content-mismatch", src.id, src.rel, a.line,
                           f"{words} words are not in the original here", a.locator))
    return problems


def expected_content(eng: Engagement, src: Source, kind: str):
    """Re-extract the original in memory, as `extract` wrote it."""
    rel = src.f("raw_file")
    fmt = src.f("source_type")
    if fmt == "pdf":
        return expected_pdf(eng, src)
    data = open_original(eng, rel)
    if fmt == "docx":
        return DocxReader(data, rel, src.id, keep_images=False).read().content
    ctx = {"data": data, "rel": rel, "format": fmt, "as": "transcript" if kind == "turns" else "document"}
    return extract_textlike(eng, ctx).content


# --- Checks (verify) ----------------------------------------------------------------------------


def callouts(src: Source) -> list:
    """(kind, rest, 1-based line) for every callout header in the content."""
    result = []
    first = src.content_first_line()
    for i, line in enumerate(src.content_lines()):
        m = CALLOUT.match(line.strip())
        if m:
            result.append((m.group(1).lower(), m.group(2).strip(), first + i))
    return result


def uncertain_section(src: Source) -> list:
    out = []
    for line in src.section_lines("Uncertain passages"):
        m = UNCERTAIN_LINE.match(line.strip())
        if m:
            out.append(m.group(1).strip())
    return out


def speaker_labels(src: Source) -> list:
    labels = []
    rows = [l.strip() for l in src.section_lines("Speakers") if l.strip().startswith("|")]
    for row in rows[2:] if len(rows) >= 2 else []:
        cells = [c.strip() for c in CELL_SPLIT.split(row.strip("|"))]
        if cells and cells[0]:
            labels.append(cells[0])
    return labels


def structure_problems(src: Source, kind: str) -> list:
    problems = []
    norm = normalize(src.content_lines(), src.content_first_line())
    if kind == "pdf":
        count = src.i("page_count") or 0
        pages = [int(PAGE_MARK.match(l.rstrip()).group(1)) for _, l in norm if PAGE_MARK.match(l.rstrip())]
        if count <= 0:
            problems.append(_p("missing-field", src.id, src.rel, None, "page_count is not set"))
        elif pages != list(range(1, count + 1)):
            missing = [n for n in range(1, count + 1) if n not in pages]
            where = f"p. {missing[0]}" if missing else None
            problems.append(_p("markers-missing", src.id, src.rel, None,
                               f"page markers must run p. 1 to p. {count} in order", where))
    elif kind == "turns":
        turns = [int(TURN_MARK.match(l.rstrip()).group(2)) for _, l in norm if TURN_MARK.match(l.rstrip())]
        if turns != list(range(1, len(turns) + 1)) or not turns:
            gap = next((n for n, t in enumerate(turns, start=1) if t != n), len(turns) + 1)
            problems.append(_p("markers-missing", src.id, src.rel, None,
                               "turn markers must run T1, T2, … without gaps", f"T{gap}"))
        labels = {TURN_MARK.match(l.rstrip()).group(1) for _, l in norm if TURN_MARK.match(l.rstrip())}
        table = set(speaker_labels(src))
        if not src.restricted and table != labels:
            problems.append(_p("bad-value", src.id, src.rel, None,
                               "## Speakers labels must be exactly the labels used in the turns"))
    paras = [int(PARA_MARK.match(l.rstrip()).group(1)) for _, l in norm if PARA_MARK.match(l.rstrip())]
    if paras and paras != list(range(1, len(paras) + 1)):
        gap = next((n for n, t in enumerate(paras, start=1) if t != n), len(paras) + 1)
        problems.append(_p("markers-missing", src.id, src.rel, None, "paragraph numbers must run ¶ 1, ¶ 2, … without gaps", f"¶ {gap}"))
    if kind == "paras" and not paras:
        problems.append(_p("markers-missing", src.id, src.rel, None, "no [¶n] paragraph markers"))
    if kind == "doc" and src.f("source_type") == "docx":
        if not paras and not any(HEADING.match(l.rstrip()) for _, l in norm):
            problems.append(_p("markers-missing", src.id, src.rel, None, "no headings and no [¶n] markers"))
    return problems


def field_problems(eng: Engagement, src: Source) -> tuple:
    problems, warnings = [], []
    f, id_, rel = src.f, src.id, src.rel
    if not src.fm_ok:
        return [_p("unparseable", id_, rel, 1, "no front matter")], warnings
    for n, error in src.fm_errors:
        problems.append(_p("unparseable", id_, rel, n, f"front matter: {error}"))
    if f("type") != "source":
        problems.append(_p("bad-value", id_, rel, None, f"type: {f('type')!r}"))
    missing = [k for k in REQUIRED if k not in src.fields or (k != "raw_bytes" and not f(k))]
    if src.i("raw_bytes") is None and "raw_bytes" not in missing:
        problems.append(_p("bad-value", id_, rel, None, "raw_bytes must be a whole number"))
    if src.is_meeting and not f("meeting_date"):
        missing.append("meeting_date")
    if f("material") == "meeting-notes":
        missing += [k for k in ("author", "author_kind") if not f(k)]
    if missing:
        problems.append(_p("missing-field", id_, rel, None, "missing: " + ", ".join(missing)))
    for key, allowed in ALLOWED.items():
        value = f(key)
        if (value or key not in ("material", "source_type")) and key in src.fields and value not in allowed:
            problems.append(_p("bad-value", id_, rel, None, f"{key}: {value!r}"))
    if f("origin") not in SOURCE_ORIGINS:
        problems.append(_p("bad-value", id_, rel, None, f"origin: {f('origin')!r} (a source's origin is never llm-inference)"))
    if f("audience") != "internal":
        problems.append(_p("client-ready", id_, rel, None, "sources stay internal"))
    if src.b("inference_confirmed"):
        problems.append(_p("bad-value", id_, rel, None, "inference_confirmed must stay false"))
    if f("confidence") == "high" and f("author_kind") == "ai-notetaker":
        problems.append(_p("confidence-cap", id_, rel, None, "an AI note-taker's summary is at most medium"))
    sha = f("raw_sha256")
    if not (SHA256.match(sha) or (sha == "" and src.restricted)):
        problems.append(_p("bad-value", id_, rel, None, "raw_sha256 must be 64 hex characters"))
    if f("fidelity") == "" and not src.restricted:
        problems.append(_p("bad-value", id_, rel, None, "fidelity is empty on an unrestricted source"))
    if f("meeting_date") and not FULL_DATE.match(f("meeting_date")):
        problems.append(_p("bad-value", id_, rel, None, "meeting_date must be YYYY-MM-DD"))
    if f("source_date") and not SOURCE_DATE.match(f("source_date")):
        problems.append(_p("bad-value", id_, rel, None, "source_date must be YYYY-MM-DD, YYYY-MM or YYYY"))
    if f("source_type") == "pdf":
        count, reviewed = src.i("page_count"), src.i("pages_reviewed")
        if count is None or reviewed is None or not 0 <= reviewed <= count:
            problems.append(_p("bad-value", id_, rel, None, "pages_reviewed must be between 0 and page_count"))
    if not src.has_markers:
        problems.append(_p("markers-missing", id_, rel, None, "the content markers are missing"))
        return problems, warnings

    found = callouts(src)
    kinds = [(k, rest) for k, rest, _ in found]
    derived_present = any(k == "derived" for k, _ in kinds) or any(
        k == "corrected" and "derived" in rest for k, rest in kinds)
    if src.b("derived") != derived_present:
        problems.append(_p("derived-flag", id_, rel, None,
                           f"derived is {str(src.b('derived')).lower()} but the content "
                           f"{'has' if derived_present else 'has no'} derived callouts"))
    derived_kinds = {rest.split()[0].lower() if rest else "" for k, rest in kinds if k == "derived"}
    method = f("extraction_method")
    content_words = [l for _, l in normalize(src.content_lines()) if l.strip()]
    notice_only = [l.strip() for l in src.content_lines() if l.strip()] == [RESTRICTED_NOTICE]
    if method == "text" and derived_kinds:
        problems.append(_p("method-mismatch", id_, rel, None, "extraction_method is text but derived callouts are present"))
    if method == "ocr" and "ocr" not in derived_kinds:
        problems.append(_p("method-mismatch", id_, rel, None, "extraction_method is ocr but there is no ocr callout"))
    if method == "vision-description" and "vision-description" not in derived_kinds:
        problems.append(_p("method-mismatch", id_, rel, None,
                           "extraction_method is vision-description but there is no vision-description callout"))
    if method == "none" and not src.restricted:
        problems.append(_p("method-mismatch", id_, rel, None, "extraction_method is none on an unrestricted source"))
    if src.restricted and not src.b("content_removed") and notice_only and method != "none":
        problems.append(_p("method-mismatch", id_, rel, None, "a restricted record must have extraction_method none"))
    if src.restricted and not notice_only and content_words:
        warnings.append(_p("restricted-has-content", id_, rel, None,
                           "restricted, but the content is still here; later skills must not read it"))
    listed = set(src.l("uncertain_passages"))
    section = set(uncertain_section(src))
    if listed != section:
        only_field = sorted(listed - section)
        only_section = sorted(section - listed)
        problems.append(_p("uncertain-mismatch", id_, rel, None,
                           f"{len(only_field)} only in uncertain_passages, {len(only_section)} only in ## Uncertain passages",
                           (only_field or only_section)[0]))
    for k, rest, line in found:
        if k == "corrected":
            if not re.match(r"^\d{4}-\d{2}-\d{2}\b", rest):
                problems.append(_p("bad-value", id_, rel, line, "a [!corrected] callout needs a date"))
            body = []
            lines = src.lines
            j = line  # 0-based index of the line after the header
            while j < len(lines) and lines[j].strip().startswith(">") and not CALLOUT.match(lines[j].strip()):
                body.append(re.sub(r"^\s*>\s?", "", lines[j]))
                j += 1
            if not any(b.startswith("was:") for b in body) or not any(b.strip() and not b.startswith("was:") for b in body):
                problems.append(_p("bad-value", id_, rel, line, "a [!corrected] callout needs a `was:` line and the new text"))
    kind = source_kind(src)
    if not src.restricted:
        problems += structure_problems(src, kind)
    return problems, warnings


def leak_problems(eng: Engagement, src: Source) -> list:
    if not (eng.uses_code_name and eng._client):
        return []
    needle = eng._client.lower()
    sections = []
    for _, section, line in src.outside_content():
        if needle in line.lower() and section not in sections:
            sections.append(section)
    return [_p("real-name-leak", src.id, src.rel, None,
               f"the real client name appears in {s}; use the code name") for s in sections]


def check_source(eng: Engagement, src: Source, compare: bool = True) -> tuple:
    """(problems, warnings, compared) for one source."""
    problems, warnings = field_problems(eng, src)
    problems += leak_problems(eng, src)
    compared = False
    rel = src.f("raw_file")
    if rel and not (eng.raw / rel).exists():
        warnings.append(_p("original-missing", src.id, src.rel, None, f"raw/{rel} not found"))
        return problems, warnings, compared
    if not compare or src.restricted or not src.has_markers or src.f("fidelity") not in ("pending", "checked"):
        if src.f("fidelity") == "unchecked":
            warnings.append(_p("fidelity-unchecked", src.id, src.rel, None,
                               "PDF text copied without poppler; spot-check it in review"))
        return problems, warnings, compared
    if not supported(src.f("source_type")):
        return problems, warnings, compared
    if eng.policy == "unconfirmed":
        warnings.append(_p("fidelity-unchecked", src.id, src.rel, None,
                           "model use is unconfirmed; the original was not opened, comparison skipped"))
        return problems, warnings, compared
    if src.f("source_type") == "pdf" and not poppler_available():
        warnings.append(_p("fidelity-unchecked", src.id, src.rel, None, "poppler not found; comparison skipped"))
        return problems, warnings, compared
    kind = source_kind(src)
    try:
        expected = expected_content(eng, src, kind)
    except Fail as exc:
        if exc.code == EXIT_POLICY:
            raise
        problems.append(_p("content-mismatch", src.id, src.rel, None,
                           "the original could not be re-read: " + _str(exc.payload.get("detail", ""))))
        return problems, warnings, compared
    if expected is None:
        return problems, warnings, compared
    problems += compare_content(expected, src, kind)
    compared = True
    return problems, warnings, compared


def global_problems(eng: Engagement, ids=None) -> tuple:
    problems, warnings = [], []
    sources = eng.sources()
    wanted = set(ids) if ids else None
    problems += [p for p in eng.id_problems() if wanted is None or p["id"] in wanted]
    by_raw, by_sha = {}, {}
    for src in sources:
        for key, table in ((src.f("raw_file"), by_raw), (src.f("raw_sha256"), by_sha)):
            if key:
                table.setdefault(key, []).append(src.id)
    for table, what in ((by_raw, "raw_file"), (by_sha, "raw_sha256")):
        for key, owners in table.items():
            if len(owners) > 1:
                for owner in owners:
                    if wanted is None or owner in wanted:
                        others = ", ".join(o for o in owners if o != owner)
                        problems.append(_p("duplicate-original", owner, f"{EXTRACTED_DIR}/{owner}.md", None,
                                           f"same {what} as {others}"))
    known = {s.id for s in sources}
    for src in sources:
        if wanted is not None and src.id not in wanted:
            continue
        for target in src.l("supersedes"):
            if target not in known:
                problems.append(_p("broken-link", src.id, src.rel, None, f"supersedes: {target} does not exist"))
    index_text = read_text(eng.root / INDEX) or ""
    rows = index_rows(index_text)
    for src in sources:
        if wanted is not None and src.id not in wanted:
            continue
        row = rows.get(src.id)
        if src.complete:
            if row is None:
                problems.append(_p("index-missing", src.id, INDEX, None, "a complete source has no index row"))
            elif " ".join(row[1].split()) != " ".join(index_row(src).split()):
                problems.append(_p("index-mismatch", src.id, INDEX, row[0], "the index row disagrees with the source"))
        elif row is not None:
            problems.append(_p("index-mismatch", src.id, INDEX, row[0], "an unfinished source has an index row"))
    if wanted is None:
        for id_, (line, _) in rows.items():
            if id_ not in known:
                problems.append(_p("index-mismatch", id_, INDEX, line, "no such source"))
    if eng.uses_code_name and eng._client:
        needle = eng._client.lower()
        for id_, (line, row) in rows.items():
            if (wanted is None or id_ in wanted) and needle in row.lower():
                problems.append(_p("real-name-leak", id_, INDEX, line, "the real client name appears in this index row"))
        log = read_text(eng.root / CHANGELOG) or ""
        for n, line in enumerate(log.split("\n"), start=1):
            if line.startswith(">") or not S_MENTION.search(line):
                continue
            mentioned = {"S-" + m for m in S_MENTION.findall(line)}
            if (wanted is None or mentioned & wanted) and needle in line.lower():
                problems.append(_p("real-name-leak", None, CHANGELOG, n, "the real client name appears in this log line"))
        # fix-unlogged: every [!corrected] callout needs an extraction-fix line for its source
    log = read_text(eng.root / CHANGELOG) or ""
    for src in sources:
        if wanted is not None and src.id not in wanted:
            continue
        fixes = sum(1 for k, _, _ in callouts(src) if k == "corrected") if src.has_markers else 0
        logged = len(re.findall(rf"^\d{{4}}-\d{{2}}-\d{{2}} · {re.escape(src.id)} @ [^·]+ · extraction-fix ·", log, re.M))
        if fixes > logged:
            warnings.append(_p("fix-unlogged", src.id, src.rel, None,
                               f"{fixes - logged} [!corrected] callout(s) without an extraction-fix line in the changelog"))
    return problems, warnings


def run_verify(eng: Engagement, ids=None) -> tuple:
    sources = eng.sources() if not ids else [eng.source(i) for i in ids]
    problems, warnings = global_problems(eng, ids)
    compared = {}
    for src in sources:
        p, w, c = check_source(eng, src)
        problems += p
        warnings += w
        compared[src.id] = c
    return problems, warnings, compared


# --- Locators per line (review) -----------------------------------------------------------------


def line_locators(src: Source) -> list:
    """[(1-based line, locator, text)] for the content region."""
    kind = source_kind(src)
    out = []
    locator = "(before the first marker)"
    path = []
    for lineno, line in zip(range(src.content_first_line(), 10 ** 9), src.content_lines()):
        s = line.rstrip()
        if kind == "pdf" and PAGE_MARK.match(s):
            locator = f"p. {PAGE_MARK.match(s).group(1)}"
        elif kind == "turns" and TURN_MARK.match(s):
            m = TURN_MARK.match(s)
            locator = m.group(3) or f"T{m.group(2)}"
        elif kind in ("paras", "doc") and PARA_MARK.match(s):
            locator = f"¶ {PARA_MARK.match(s).group(1)}"
        elif kind == "doc" and s in UNIT_COMMENTS:
            locator = UNIT_COMMENTS[s]
        elif kind == "doc" and HEADING.match(s):
            m = HEADING.match(s)
            level = len(m.group(1))
            path = [(l, t) for l, t in path if l < level] + [(level, " ".join(m.group(2).split()))]
            locator = "§ " + " > ".join(t for _, t in path)
        out.append((lineno, locator, line))
    return out


# --- Commands ----------------------------------------------------------------------------------


def source_summary(eng: Engagement, src: Source) -> dict:
    rel = src.f("raw_file")
    return {
        "id": src.id, "title": src.f("title"), "material": src.f("material"), "status": src.f("status"),
        "extraction_status": src.f("extraction_status"), "restricted": src.restricted, "raw_file": rel,
        "original_present": bool(rel) and os.path.lexists(str(eng.raw / rel)), "derived": src.b("derived"),
        "uncertain": len(src.l("uncertain_passages")), "supersedes": src.l("supersedes"),
        "fidelity": src.f("fidelity"), "page_count": src.i("page_count") or 0,
        "pages_reviewed": src.i("pages_reviewed") or 0,
    }


def raw_state(eng: Engagement, rel: str, fmt: str) -> tuple:
    sources = eng.by_raw(rel)
    if sources:
        src = sources[0]
        for s in sources:
            if s.restricted:
                return "restricted", s.id
        if src.f("status") == "rejected" and not src.complete:
            return "rejected", src.id
        return ("ingested" if src.complete else "in-progress"), src.id
    return ("new" if supported(fmt) else "unsupported"), None


def possible_restricted_copy(eng: Engagement, rel: str, size: int):
    stem = version_stem(rel)
    for src in eng.sources():
        if not src.restricted:
            continue
        other = src.f("raw_file")
        if other == rel:
            continue
        if src.i("raw_bytes") == size or (other and version_stem(other) == stem):
            return src.id
    return None


def raw_entry(eng: Engagement, rel: str, size: int) -> dict:
    fmt = raw_format(rel)
    state, source_id = raw_state(eng, rel, fmt)
    entry = {"raw": rel, "format": fmt, "bytes": size, "state": state, "source_id": source_id}
    entry["possible_restricted_copy"] = possible_restricted_copy(eng, rel, size) if state == "new" else None
    return entry


def cmd_status(eng: Engagement, args) -> tuple:
    files = eng.raw_files()
    if args.raw:
        sizes = dict(files)
        listed = []
        for arg in args.raw:
            try:
                rel, path = eng.resolve_raw(arg)
            except Fail as exc:
                state = "outside-raw" if exc.payload.get("reason") == "outside-raw" else "missing"
                listed.append({"raw": arg, "format": raw_format(arg), "bytes": None, "state": state,
                               "source_id": None, "possible_restricted_copy": None})
                continue
            listed.append(raw_entry(eng, rel, sizes.get(rel, os.stat(str(path)).st_size)))
        raw_files = listed
    else:
        raw_files = [raw_entry(eng, rel, size) for rel, size in files]
    work = []
    work_root = eng.root / WORK_DIR
    if work_root.is_dir():
        ids = {s.id: s for s in eng.sources()}
        for folder in sorted(work_root.iterdir()):
            if folder.is_dir():
                src = ids.get(folder.name)
                if src is None or src.complete:
                    work.append({"id": folder.name, "path": folder.relative_to(eng.root).as_posix(),
                                 "reason": "source complete" if src else "source missing"})
    problems, _ = global_problems(eng)
    problems = [p for p in problems if p["code"] in ("duplicate-id", "malformed-id", "unparseable", "duplicate-original")]
    available = poppler_available()
    return EXIT_OK, {
        "engagement": eng.engagement_block(),
        "pdf_backend": {"available": available, "mode": "checked" if available else "unchecked",
                        "tools": list(POPPLER), "install_hint": INSTALL_HINT},
        "raw_files": raw_files,
        "sources": [source_summary(eng, s) for s in eng.sources()],
        "next_id": eng.next_id(),
        "work_folders": work,
        "problems": problems,
    }


def _origin_for(material: str) -> str:
    return "client-document" if material == "document" else "interview-meeting"


def cmd_extract(eng: Engagement, args) -> tuple:
    rel, path = eng.resolve_raw(args.raw)
    fmt = raw_format(rel)
    if not supported(fmt):
        raise Fail(EXIT_CANT_EXTRACT, {"reason": "unsupported", "raw": rel, "format": fmt,
                                       "detail": "Not supported yet. Nothing was opened or written."})
    existing = eng.by_raw(rel)
    for src in existing:
        if src.restricted:
            raise Fail(EXIT_POLICY, {"refused": "restricted-source", "restricted_source": src.id,
                                     "detail": "This file is registered as restricted. No file was opened."})
    if eng.policy == "unconfirmed":
        raise Fail(EXIT_POLICY, {"refused": "policy-unconfirmed",
                                 "detail": "Settle model use with charter first. No file was opened."})
    for src in existing:
        if src.f("status") == "rejected" and not src.complete:
            raise Fail(EXIT_USAGE, {"reason": "rejected", "source_id": src.id, "raw": rel,
                                    "detail": "This file was rejected while extracting. Nothing was opened."})
    if eng.policy == "restricted" and not args.sendable:
        raise Fail(EXIT_POLICY, {"refused": "policy-restricted-needs-consent",
                                 "detail": "Ask the consultant whether this file may be sent, then pass "
                                           "--sendable. No file was opened."})
    size = os.stat(str(path)).st_size
    if not existing:
        copy_of = possible_restricted_copy(eng, rel, size)
        if copy_of and not args.sendable:
            raise Fail(EXIT_POLICY, {"refused": "possible-restricted-copy", "restricted_source": copy_of,
                                     "detail": "This file may be a copy of a restricted file. Ask the consultant "
                                               "whether it may be sent, then pass --sendable. No file was opened."})
    in_progress = [s for s in existing if not s.complete]
    complete = [s for s in existing if s.complete]
    if complete:
        raise Fail(EXIT_USAGE, {"reason": "already-ingested", "source_id": complete[0].id, "raw": rel})
    if in_progress and not args.restart:
        src = in_progress[0]
        return EXIT_OK, {
            "id": src.id, "file": src.rel, "resumed": True, "raw": rel, "format": fmt,
            "material_guess": src.f("material") or "document", "origin_guess": src.f("origin"),
            "pdf": ({"page_count": src.i("page_count") or 0, "pages_reviewed": src.i("pages_reviewed") or 0,
                     "mode": "unchecked" if src.f("fidelity") == "unchecked" else "checked"}
                    if fmt == "pdf" else None),
            "docx": None, "transcript": None, "uncertain": src.l("uncertain_passages"),
            "version_candidates": version_candidates(eng, rel, exclude=src.id),
            "next": (f"continue from page {(src.i('pages_reviewed') or 0) + 1}" if fmt == "pdf"
                     else "continue where you stopped; run verify, then finalize"),
        }
    data = open_original(eng, rel)
    sha = hashlib.sha256(data).hexdigest()
    for other in eng.sources():
        if other.f("raw_file") != rel and other.f("raw_sha256") == sha:
            raise Fail(EXIT_DUPLICATE, {"duplicate_of": other.id, "raw": rel,
                                        "detail": f"Identical to {other.id}. Nothing was written."})
    id_ = in_progress[0].id if in_progress else eng.next_id()
    ctx = {"data": data, "rel": rel, "format": fmt, "as": args.as_, "id": id_}
    ext = EXTRACTORS[fmt](eng, ctx)
    fields = default_fields(id_)
    if in_progress:
        old = in_progress[0]
        for key in ("title", "created", "provided_by", "source_date", "supersedes", "change_reason", "change_trigger"):
            if key in old.fields:
                fields[key] = old.fields[key]
    fields.update({
        "material": ext.material, "origin": _origin_for(ext.material), "source_type": fmt,
        "raw_file": rel, "raw_sha256": sha, "raw_bytes": size,
        "uncertain_passages": [loc for loc, _ in ext.uncertain],
    })
    fields.update(ext.fields)
    target = eng.extracted / f"{id_}.md"
    work = eng.root / WORK_DIR / id_
    if work.exists():
        shutil.rmtree(str(work))
    if ext.images:
        work.mkdir(parents=True, exist_ok=True)
        for name, blob in ext.images:
            (work / name).write_bytes(blob)
    eng.extracted.mkdir(parents=True, exist_ok=True)
    atomic_write(target, render_source(fields, ext.speakers, ext.uncertain, ext.content))
    result = {
        "id": id_, "file": target.relative_to(eng.root).as_posix(), "resumed": False, "raw": rel,
        "format": fmt, "material_guess": ext.material, "origin_guess": _origin_for(ext.material),
        "pdf": None, "docx": None, "transcript": None,
        "uncertain": [f"{loc} — {why}" for loc, why in ext.uncertain],
        "version_candidates": version_candidates(eng, rel, exclude=id_),
        "next": ext.next,
    }
    if ext.block_name:
        result[ext.block_name] = ext.block
    return EXIT_OK, result


def version_candidates(eng: Engagement, rel: str, exclude: str) -> list:
    stem = version_stem(rel)
    return [s.id for s in eng.sources()
            if s.id != exclude and not s.restricted and s.f("raw_file") and s.f("raw_file") != rel
            and version_stem(s.f("raw_file")) == stem]


def cmd_register_restricted(eng: Engagement, args) -> tuple:
    rel, path = eng.resolve_raw(args.raw)
    if eng.policy == "unconfirmed":
        raise Fail(EXIT_POLICY, {"refused": "policy-unconfirmed",
                                 "detail": "Settle model use with charter first. No file was opened."})
    existing = eng.by_raw(rel)
    if existing:
        raise Fail(EXIT_USAGE, {"error": "already-registered", "source_id": existing[0].id, "raw": rel})
    material = args.material or ""
    if material and material not in MATERIALS:
        raise Fail(EXIT_USAGE, {"error": "bad-material", "detail": f"material must be one of {', '.join(MATERIALS)}"})
    if args.source_date and not SOURCE_DATE.match(args.source_date):
        raise Fail(EXIT_USAGE, {"error": "bad-date", "detail": "source date must be YYYY-MM-DD, YYYY-MM or YYYY"})
    size = os.stat(str(path)).st_size  # stat only: the file is never opened or hashed
    id_ = eng.next_id()
    fmt = raw_format(rel)
    fields = default_fields(id_)
    fields.update({
        "title": " ".join((args.title or "").split()), "material": material,
        "origin": _origin_for(material) if material else "", "source_type": fmt if supported(fmt) else "other",
        "raw_file": rel, "raw_sha256": "", "raw_bytes": size, "provided_by": " ".join((args.provided_by or "").split()),
        "source_date": args.source_date or "", "extraction_status": "complete", "fidelity": "",
        "extraction_method": "none", "restricted": True,
    })
    if material in MEETINGS and args.source_date and FULL_DATE.match(args.source_date):
        fields["meeting_date"] = args.source_date
    text = render_source(fields, None, [], RESTRICTED_NOTICE)
    target = eng.extracted / f"{id_}.md"
    src = Source(target, target.relative_to(eng.root).as_posix(), text)
    index_path = eng.root / INDEX
    index = upsert_index(read_text(index_path) or "", {id_: index_row(src)})
    eng.extracted.mkdir(parents=True, exist_ok=True)
    atomic_write(target, text)
    atomic_write(index_path, index)
    return EXIT_OK, {"id": id_, "file": src.rel, "index_row": index_row(src)}


def cmd_verify(eng: Engagement, args) -> tuple:
    problems, warnings, _ = run_verify(eng, args.ids or None)
    return (EXIT_PROBLEMS if problems else EXIT_OK), {"problems": problems, "warnings": warnings}


def cmd_finalize(eng: Engagement, args) -> tuple:
    src = eng.source(args.id)
    if src.complete:
        raise Fail(EXIT_USAGE, {"error": "not-in-progress", "id": src.id, "detail": "the source is already complete"})
    if src.f("status") == "rejected":
        raise Fail(EXIT_USAGE, {"error": "rejected", "id": src.id})
    problems, warnings, compared = run_verify(eng, [src.id])
    if src.f("source_type") == "pdf":
        count, reviewed = src.i("page_count") or 0, src.i("pages_reviewed") or 0
        if reviewed < count:
            problems.append(_p("pages-incomplete", src.id, src.rel, None,
                               f"{reviewed} of {count} pages reviewed", f"p. {reviewed + 1}"))
    if src.f("fidelity") == "pending" and not compared.get(src.id):
        problems.append(_p("fidelity-unchecked", src.id, src.rel, None,
                           "the text could not be compared with the original, so the source can't be finalized"))
    if problems:
        return EXIT_PROBLEMS, {"id": src.id, "problems": problems, "warnings": warnings}
    updates = {"extraction_status": "complete"}
    if src.f("fidelity") == "pending":
        updates["fidelity"] = "checked"
    text = with_fields(src, updates)
    done = Source(src.path, src.rel, text)
    row = index_row(done)
    index_path = eng.root / INDEX
    index = upsert_index(read_text(index_path) or "", {src.id: row})
    atomic_write(src.path, text)
    atomic_write(index_path, index)
    work = eng.root / WORK_DIR / src.id
    if work.exists():
        shutil.rmtree(str(work))
    return EXIT_OK, {"id": src.id, "index_row": row, "warnings": warnings}


def refs_for(eng: Engagement, ids: list) -> dict:
    wanted = {id_: re.compile(rf"\b{re.escape(id_)}\b") for id_ in ids}
    refs: dict = {id_: [] for id_ in ids}
    for rel, text in sorted(eng.scan_texts().items()):
        if rel == CHANGELOG:
            continue
        parsed = parse_file(text, rel)
        objects = []
        own = _str(parsed["front"].get("id"))
        if own:
            objects.append((own, parsed["front"]))
        objects += [(e["id"], e["fields"]) for e in parsed["entries"]]
        for obj_id, fields in objects:
            for key in REF_FIELDS:
                values = fields.get(key)
                values = values if isinstance(values, list) else [values]
                for id_, pattern in wanted.items():
                    if any(isinstance(v, str) and pattern.search(v) for v in values):
                        refs[id_].append({"id": obj_id, "field": key, "file": rel})
    return refs


def cmd_refs(eng: Engagement, args) -> tuple:
    for id_ in args.ids:
        if not ID_TOKEN.match(id_):
            raise Fail(EXIT_USAGE, {"error": "bad-id", "detail": f"not an object ID: {id_!r} (expected for example S-003)"})
    return EXIT_OK, {"refs": refs_for(eng, args.ids)}


def _reason(text: str) -> str:
    return " ".join((text or "").split()).replace(" · ", " - ")


def _log_line(subject: str, event: str, reason: str, trigger: str) -> str:
    shown = trigger.replace("-", " ") if trigger in TRIGGERS else trigger
    return f"{date.today().isoformat()} · {subject} · {event} · {_reason(reason)} · {shown}"


def write_all(eng: Engagement, texts: dict) -> None:
    """Write several files; all are rendered first, so a failure in rendering writes nothing."""
    for path, text in texts.items():
        atomic_write(path, text)


def cmd_set_status(eng: Engagement, args) -> tuple:
    src = eng.source(args.id)
    status = src.f("status")
    if status in ("superseded", "rejected"):
        raise Fail(EXIT_USAGE, {"error": "closed", "id": src.id, "detail": f"the source is already {status}"})
    reason, trigger = _reason(args.reason), args.trigger or ""
    changed, log, texts = [], [], {}
    index_updates = {}
    if args.status == "rejected":
        if not reason or not trigger:
            raise Fail(EXIT_USAGE, {"error": "reason-and-trigger-required",
                                    "detail": "rejecting needs --reason and --trigger"})
        text = with_fields(src, {"status": "rejected", "change_reason": reason, "change_trigger": trigger})
        texts[src.path] = text
        changed.append({"id": src.id, "status": "rejected"})
        log.append(_log_line(src.id, "reject", reason, trigger))
        if src.complete:
            index_updates[src.id] = index_row(Source(src.path, src.rel, text))
        refs_ids = [src.id]
    else:
        if not src.complete:
            raise Fail(EXIT_USAGE, {"error": "not-complete", "id": src.id,
                                    "detail": "only a complete source can be approved; finish it with finalize"})
        text = with_fields(src, {"status": "active"})
        texts[src.path] = text
        changed.append({"id": src.id, "status": "active"})
        index_updates[src.id] = index_row(Source(src.path, src.rel, text))
        refs_ids = []
        old_ids = src.l("supersedes")
        if old_ids:
            why, how = src.f("change_reason"), src.f("change_trigger")
            if not why or how not in TRIGGERS:
                raise Fail(EXIT_USAGE, {"error": "reason-and-trigger-required", "id": src.id,
                                        "detail": "a new version needs change_reason and change_trigger before approval"})
            for old_id in old_ids:
                old = eng.source(old_id)
                if old.f("status") in ("superseded", "rejected"):
                    continue
                old_text = with_fields(old, {"status": "superseded", "change_reason": why, "change_trigger": how})
                texts[old.path] = old_text
                changed.append({"id": old.id, "status": "superseded"})
                if old.complete:
                    index_updates[old.id] = index_row(Source(old.path, old.rel, old_text))
                log.append(_log_line(f"{old.id} → {src.id}", "supersede", why, how))
                refs_ids.append(old.id)
    index_path = eng.root / INDEX
    if index_updates:
        texts[index_path] = upsert_index(read_text(index_path) or "", index_updates)
    if log:
        log_path = eng.root / CHANGELOG
        text = read_text(log_path) or ""
        for line in log:
            text = append_changelog(text, line)
        texts[log_path] = text
    write_all(eng, texts)
    return EXIT_OK, {"changed": changed, "log": log, "refs": refs_for(eng, refs_ids) if refs_ids else {}}


def cmd_restrict(eng: Engagement, args) -> tuple:
    src = eng.source(args.id)
    reason = _reason(args.reason)
    if not reason:
        raise Fail(EXIT_USAGE, {"error": "reason-required"})
    if args.remove_content and not " ".join((args.by or "").split()):
        raise Fail(EXIT_USAGE, {"error": "by-required", "detail": "--remove-content needs --by NAME"})
    if not src.complete:
        raise Fail(EXIT_USAGE, {"error": "not-complete", "id": src.id,
                                "detail": "restrict a complete source; an unfinished one can be rejected instead"})
    if src.restricted and not args.remove_content:
        raise Fail(EXIT_USAGE, {"error": "already-restricted", "id": src.id})
    if src.b("content_removed"):
        raise Fail(EXIT_USAGE, {"error": "already-removed", "id": src.id})
    log = []
    updates = {"restricted": True}
    if not src.restricted:
        log.append(_log_line(src.id, "restrict", reason, "-"))
    text = with_fields(src, updates)
    if args.remove_content:
        by = " ".join(args.by.split())
        current = Source(src.path, src.rel, text)
        lines = current.lines
        # Rebuild the Speakers and Uncertain sections empty, and the content region as the notice.
        new_lines = []
        skip_until = None
        i = 0
        while i < len(lines):
            if current.c_start is not None and i == current.c_start:
                new_lines += [CONTENT_START, RESTRICTED_NOTICE, CONTENT_END]
                i = current.c_end + 1
                continue
            line = lines[i]
            if i >= current.body_start and line.startswith("## ") and line[3:].strip() in ("Speakers", "Uncertain passages"):
                new_lines += [line, ""]
                if line[3:].strip() == "Speakers":
                    new_lines += ["| Label | Confirmed name |", "|---|---|", ""]
                j = i + 1
                while j < len(lines) and not lines[j].startswith("## ") and not (current.c_start is not None and j == current.c_start):
                    j += 1
                i = j
                continue
            new_lines.append(line)
            i += 1
        text = "\n".join(new_lines)
        cleared = Source(src.path, src.rel, text)
        text = with_fields(cleared, {"content_removed": True, "extraction_method": "none", "derived": False,
                                     "uncertain_passages": []})
        log.append(_log_line(src.id, "remove-content", reason, "-") + f"\n> content removed on instruction of {by}")
    final = Source(src.path, src.rel, text)
    texts = {src.path: text}
    index_path = eng.root / INDEX
    texts[index_path] = upsert_index(read_text(index_path) or "", {src.id: index_row(final)})
    log_path = eng.root / CHANGELOG
    log_text = read_text(log_path) or ""
    for line in log:
        log_text = append_changelog(log_text, line)
    texts[log_path] = log_text
    write_all(eng, texts)
    if args.remove_content:
        work = eng.root / WORK_DIR / src.id
        if work.exists():
            shutil.rmtree(str(work))
    return EXIT_OK, {"id": src.id, "removed": bool(args.remove_content), "log": log, "refs": refs_for(eng, [src.id])}


def sample_pages(src: Source) -> list:
    words = Counter()
    norm = normalize(src.content_lines(), src.content_first_line())
    page = None
    for _, line in norm:
        m = PAGE_MARK.match(line.rstrip())
        if m:
            page = int(m.group(1))
            words[page] += 0
            continue
        if page is not None:
            words[page] += len(line.split())
    pages = [p for p in sorted(words) if words[p]]
    if len(pages) <= 3:
        return pages
    return sorted({pages[0], pages[len(pages) // 2], pages[-1]})


def review_source(src: Source) -> dict:
    if src.restricted:
        return {"id": src.id, "title": src.f("title"), "status": src.f("status"), "restricted": True}
    located = line_locators(src)
    derived, corrected, tables = [], [], []
    comments = tracked = 0
    in_callout = False
    table_start = None
    rows = cols = 0
    built_by = "assistant" if src.f("source_type") == "pdf" else "script"

    def close_table():
        if table_start is not None:
            tables.append({"locator": table_start[1], "rows": rows, "cols": cols, "line": table_start[0],
                           "built_by": built_by})

    for lineno, locator, line in located:
        s = line.strip()
        m = CALLOUT.match(s)
        if m:
            in_callout = True
            kind = m.group(1).lower()
            if kind == "derived":
                derived.append({"locator": locator, "kind": (m.group(2).split() or [""])[0], "line": lineno})
            elif kind == "corrected":
                corrected.append({"locator": locator, "line": lineno})
                if "derived" in m.group(2):
                    derived.append({"locator": locator, "kind": "corrected", "line": lineno})
            elif kind == "comment":
                comments += 1
        elif not s.startswith(">"):
            in_callout = False
        tracked += line.count("{++") + line.count("{--")
        if s.startswith("|") and not in_callout:
            if table_start is None:
                table_start, rows, cols = (lineno, locator), 0, 0
            if not TABLE_SEPARATOR.match(s):
                rows += 1
                cols = max(cols, len(CELL_SPLIT.split(s.strip("|"))))
        else:
            close_table()
            table_start = None
    close_table()
    starts = {}
    for lineno, locator, _ in located:
        starts.setdefault(locator, lineno)
    section_line = {}
    if "Uncertain passages" in src.sections:
        start, end = src.sections["Uncertain passages"]
        for i in range(start + 1, end):
            m = UNCERTAIN_LINE.match(src.lines[i].strip())
            if m:
                section_line.setdefault(m.group(1).strip(), i + 1)
    uncertain = [{"locator": loc, "line": starts.get(loc) or section_line.get(loc)} for loc in src.l("uncertain_passages")]
    out = {"id": src.id, "title": src.f("title"), "status": src.f("status"), "derived": derived,
           "tables": tables, "uncertain": uncertain, "corrected": corrected, "comments": comments,
           "tracked_changes": tracked, "fidelity": src.f("fidelity")}
    if src.f("fidelity") == "unchecked":
        out["sample_pages"] = sample_pages(src)
    return out


def cmd_review(eng: Engagement, args) -> tuple:
    sources = []
    for id_ in args.ids:
        src = eng.source(id_)
        if not src.complete:
            raise Fail(EXIT_USAGE, {"error": "not-complete", "id": src.id,
                                    "detail": "finish the extraction with /ingest first"})
        sources.append(src)
    reviews = [review_source(s) for s in sources]
    reviews.sort(key=lambda r: 0 if r.get("fidelity") == "unchecked" else 1)
    return EXIT_OK, {"sources": reviews}


# --- Entry point ---------------------------------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="ingest.py", description="Helper for the Cairn `ingest` skill.")
    parser.add_argument("--root", help="engagement folder (skips discovery)")
    parser.add_argument("--version", action="version", version=f"ingest.py {SCRIPT_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    status = sub.add_parser("status", help="engagement facts, raw files, sources, next ID")
    status.add_argument("raw", nargs="*", metavar="RAW")
    extract = sub.add_parser("extract", help="extract one original into an in-progress source")
    extract.add_argument("raw", metavar="RAW")
    extract.add_argument("--as", dest="as_", choices=("document", "transcript"))
    extract.add_argument("--sendable", action="store_true")
    extract.add_argument("--restart", action="store_true")
    reg = sub.add_parser("register-restricted", help="record a restricted original without opening it")
    reg.add_argument("raw", metavar="RAW")
    reg.add_argument("--title", default="")
    reg.add_argument("--material", default="")
    reg.add_argument("--source-date", default="")
    reg.add_argument("--provided-by", default="")
    verify = sub.add_parser("verify", help="check sources; exit 1 when there are problems")
    verify.add_argument("ids", nargs="*", metavar="ID")
    fin = sub.add_parser("finalize", help="mark an in-progress source complete and add its index row")
    fin.add_argument("id", metavar="ID")
    review = sub.add_parser("review", help="what to spot-check in each source (locators and lines only)")
    review.add_argument("ids", nargs="+", metavar="ID")
    setst = sub.add_parser("set-status", help="approve or reject a source")
    setst.add_argument("id", metavar="ID")
    setst.add_argument("status", choices=("active", "rejected"))
    setst.add_argument("--reason", default="")
    setst.add_argument("--trigger", choices=TRIGGERS)
    restrict = sub.add_parser("restrict", help="mark a source restricted (optionally remove its content)")
    restrict.add_argument("id", metavar="ID")
    restrict.add_argument("--reason", required=True)
    restrict.add_argument("--remove-content", action="store_true")
    restrict.add_argument("--by", default="")
    refs = sub.add_parser("refs", help="objects whose fields cite the given IDs")
    refs.add_argument("ids", nargs="+", metavar="ID")
    return parser


COMMANDS = {
    "status": cmd_status, "extract": cmd_extract, "register-restricted": cmd_register_restricted,
    "verify": cmd_verify, "finalize": cmd_finalize, "review": cmd_review, "set-status": cmd_set_status,
    "restrict": cmd_restrict, "refs": cmd_refs,
}


def _emit(obj) -> None:
    out = json.dumps(obj, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(out.encode("utf-8"))
    sys.stdout.flush()


def main(argv=None, script_path=__file__) -> int:
    args = build_parser().parse_args(argv)
    eng = None
    try:
        eng = Engagement(find_root(args.root, script_path=script_path))
        code, result = COMMANDS[args.command](eng, args)
    except Fail as exc:
        payload = dict(exc.payload)
        if exc.code == EXIT_NO_ENGAGEMENT:
            if payload.get("error") == NOT_IN_ENGAGEMENT:
                payload = {"error": "not-in-engagement", "detail": NOT_IN_ENGAGEMENT}
            sys.stderr.write(payload.get("detail", NOT_IN_ENGAGEMENT) + "\n")
        _emit(eng.redact(payload) if eng else payload)
        return exc.code
    _emit(eng.redact(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
