#!/usr/bin/env python3
"""Helper for the `extract-observations` skill: gate sources, check drafted observations, write them.

    python3 observe.py [--root PATH] status [S-ID ...]
    python3 observe.py [--root PATH] prepare S-ID [--confirmed]
    python3 observe.py [--root PATH] add DRAFTS.json [--dry-run] [--confirmed]
    python3 observe.py [--root PATH] progress S-ID (--stopped-at LOCATOR | --done) [--steering-from DRAFTS.json]
    python3 observe.py [--root PATH] tag O-ID Q-ID [Q-ID ...]
    python3 observe.py [--root PATH] verify [O-ID ...]
    python3 observe.py --version

Contract: specs/005-extract-observations/contracts/observe-script.md. Python 3.9+, standard
library only, no network, no subprocesses.

Rules this script keeps:
- Nothing under `10-sources/raw/` is ever opened.
- A source's content region is read only when the source is eligible: model use is not
  `unconfirmed`, the source is not restricted and its content not removed (the index row is
  checked before the file is opened), extraction is complete, its origin is not
  `llm-inference`, and it is not retired unless `--confirmed`.
- Stdout is one JSON object. It never prints source text beyond the claims and passages of
  existing observations. The real client name never appears in it when a code name is set.
- Every write is atomic (temp file + `os.replace`). Only `add` creates observation files
  (in `_inbox/`, `status: proposed`, `audience: internal`, no links); only `tag` edits an
  existing one, and only its `questions` line.

It does not import `cairn`, `ingest.py` or `charter.py`: each engagement runs the copy pinned
to its own framework version. The parsing and content-unit helpers are copied from
`ingest.py` and kept identical by a parity test.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

SCRIPT_VERSION = "0.5.0"

EXIT_OK, EXIT_PROBLEMS, EXIT_NO_ENGAGEMENT, EXIT_POLICY, EXIT_USAGE = 0, 1, 2, 3, 6

NOT_IN_ENGAGEMENT = (
    "Not inside a Cairn engagement. Create one with `cairn init`, then run "
    "`extract-observations` from inside it."
)
UNCONFIRMED_MESSAGE = "Model use is unconfirmed. Settle it with /charter first. No source was read."

RAW_DIR = "10-sources/raw"
EXTRACTED_DIR = "10-sources/extracted"
INDEX = "10-sources/index.md"
QUESTIONS = "00-charter/questions.md"
CHANGELOG = "60-log/changelog.md"
TEMPLATE = "_templates/observation.md"
INBOX = "_inbox"
OBSERVATIONS = "30-observations"
WORK_DIR = ".cairn/work/extract-observations"
PROGRESS = WORK_DIR + "/progress.json"

CONTENT_START = "<!-- cairn:content:start -->"
CONTENT_END = "<!-- cairn:content:end -->"
MEETINGS = ("meeting-transcript", "meeting-notes")

ID_TOKEN = re.compile(r"^[A-Z]-\d{3,}$")
SOURCE_ID = re.compile(r"^S-\d{3,}$")
OBS_ID = re.compile(r"^O-\d{3,}$")
QUESTION_ID = re.compile(r"^Q-\d{3,}$")
O_MENTION = re.compile(r"\bO-(\d{3,})\b")
ANY_ID = re.compile(r"\b([A-Z]-\d{3,})\b")
YAML_FENCE = re.compile(r"^```\s*ya?ml\s*$")
STRICT_HEADING = re.compile(r"^## ([A-Z])-(\d{3,}): (\S.*)$")
LOOSE_HEADING = re.compile(r"^## ([A-Z]{1,3}-[^\s:]*)")
KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")
LIST_ITEM = re.compile(r"^\s*-(?:\s+(.*))?$")

# Markers inside the content region (003 data-model §3.4), as in ingest.py.
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

# Observation fields (data-model §1).
LEVELS = {"low": 0, "medium": 1, "high": 2}
STATUSES = ("proposed", "active", "superseded", "rejected")
AUDIENCES = ("internal", "client-ready")
PASSAGE_KINDS = ("", "text", "table-row", "comment", "tracked-change")
LINK_FIELDS = ("supports", "contradicts", "derived_from", "supersedes", "clarifies")
SKILL_FIELDS = (
    "id", "type", "title", "status", "origin", "confidence", "confidence_reason",
    "inference_confirmed", "audience", "supports", "contradicts", "derived_from", "supersedes",
    "clarifies", "change_reason", "change_trigger", "created", "source", "locator", "questions",
    "derived", "speaker", "passage_kind", "translated",
)
BARE_VALUES = ("type", "status", "origin", "confidence", "audience", "passage_kind")
DRAFT_REQUIRED = ("source", "locator", "quote", "claim", "title", "confidence", "confidence_reason")
STORED_REQUIRED = ("id", "title", "origin", "confidence", "confidence_reason", "source", "locator")
WARNING_CODES = ("same-passage", "attribution-missing", "summary-attribution-missing",
                 "kind-unstated", "question-retired")
TITLE_MAX = 80
UNCERTAIN_PREFIX = "uncertain extraction: "
ELLIPSES = ("…", "...")
SEP = " › "


class Fail(Exception):
    """Stop with an exit code and a JSON payload."""

    def __init__(self, code: int, payload):
        if isinstance(payload, str):
            payload = {"error": payload}
        super().__init__(json.dumps(payload))
        self.code = code
        self.payload = payload


# --- Parsing (copied from ingest.py; keep identical, see test_ingest_parity.py) ----------


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


# --- Sources and content units (copied from ingest.py; keep identical) ----------------------


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


# --- Small helpers ----------------------------------------------------------------------------


def _one_line(text) -> str:
    return " ".join(_str(text).split())


def _today() -> str:
    return date.today().isoformat()


def _p(code, id_, file, detail, **extra) -> dict:
    out = {"code": code, "id": id_, "file": file, "detail": detail}
    out.update(extra)
    return out


def read_head(path: Path):
    """The front matter lines of a file, reading no further than the closing `---`."""
    try:
        with open(str(path), encoding="utf-8", errors="replace") as fh:
            first = fh.readline()
            if first.strip() != "---":
                return None
            lines = []
            for line in fh:
                if line.strip() == "---":
                    return lines
                lines.append(line.rstrip("\n").rstrip("\r"))
    except OSError:
        return None
    return None


class SourceHead:
    """What the gates need about a source, from the index row and the front matter only."""

    def __init__(self, id_: str, path: Path, rel: str, fields: dict, index_restricted: bool, readable: bool):
        self.id, self.path, self.rel = id_, path, rel
        self.fields = fields
        self.index_restricted = index_restricted
        self.readable = readable

    def f(self, key: str) -> str:
        return _str(self.fields.get(key)).strip()

    def b(self, key: str) -> bool:
        return _bool(self.fields.get(key))

    def l(self, key: str) -> list:
        return as_list(self.fields.get(key))

    @property
    def restricted(self) -> bool:
        return self.index_restricted or self.b("restricted")

    @property
    def content_removed(self) -> bool:
        return self.b("content_removed")


# --- The engagement ---------------------------------------------------------------------------


class Engagement:
    def __init__(self, root: Path):
        self.root = root
        lines = read_head(root / "engagement.md")
        if lines is None:
            raise Fail(EXIT_NO_ENGAGEMENT, {"error": "engagement-unreadable",
                                            "detail": "The engagement record (engagement.md) could not be read."})
        record, _ = parse_mapping(lines, 2)
        # The real client name is kept here only, for the leak check and output redaction.
        self._client = _str(record.get("client")).strip()
        self.code_name = _str(record.get("client_code_name")).strip()
        self.engagement_name = _str(record.get("engagement_name")).strip()
        policy = _str(record.get("model_use")).strip()
        self.model_use = policy if policy in ("allowed", "restricted") else "unconfirmed"
        self._heads = None
        self._observations = None
        self._questions = None
        self._content = {}

    @property
    def uses_code_name(self) -> bool:
        return bool(self.code_name)

    @property
    def client_label(self) -> str:
        return self.code_name or self._client

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

    def leaks(self, text: str) -> bool:
        if not (self.uses_code_name and self._client):
            return False
        return re.search(r"(?<!\w)" + re.escape(self._client) + r"(?!\w)", text or "", re.I) is not None

    def require_policy(self) -> None:
        if self.model_use == "unconfirmed":
            raise Fail(EXIT_POLICY, {"error": "policy-unconfirmed", "message": UNCONFIRMED_MESSAGE})

    # questions

    def questions(self) -> list:
        if self._questions is None:
            text = read_text(self.root / QUESTIONS) or ""
            found = []
            for entry in parse_file(text, QUESTIONS)["entries"]:
                fields = entry["fields"]
                id_ = _str(fields.get("id")).strip() or entry["id"]
                if not QUESTION_ID.match(id_):
                    continue
                found.append({"id": id_, "title": _one_line(fields.get("title")) or entry["title"],
                              "status": _str(fields.get("status")).strip()})
            self._questions = found
        return self._questions

    def question_ids(self) -> dict:
        return {q["id"]: q for q in self.questions()}

    # sources

    def index_rows(self) -> dict:
        """S-ID → the index row's cells (ID, Title, Type, Date, Origin, Status, Restricted)."""
        text = read_text(self.root / INDEX) or ""
        rows = {}
        for line in text.split("\n"):
            m = re.match(r"^\|\s*(S-\d{3,})\s*\|", line)
            if m:
                rows.setdefault(m.group(1), [c.strip() for c in CELL_SPLIT.split(line.strip().strip("|"))])
        return rows

    def index_restricted(self) -> set:
        return {id_ for id_, cells in self.index_rows().items() if cells and cells[-1].lower() == "yes"}

    def heads(self) -> list:
        if self._heads is None:
            folder = self.root / EXTRACTED_DIR
            rows = self.index_rows()
            restricted = self.index_restricted()
            result = []
            for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
                rel = path.relative_to(self.root).as_posix()
                if path.stem in restricted:
                    # Never opened: the index already says the source is restricted.
                    cells = rows[path.stem] + [""] * 7
                    fields = {"title": cells[1].replace("\\|", "|"), "material": cells[2], "origin": cells[4],
                              "status": cells[5], "restricted": True}
                    result.append(SourceHead(path.stem, path, rel, fields, True, False))
                    continue
                lines = read_head(path)
                fields = parse_mapping(lines, 2)[0] if lines is not None else {}
                id_ = _str(fields.get("id")).strip() or path.stem
                result.append(SourceHead(id_, path, rel, fields, id_ in restricted, lines is not None))
            self._heads = result
        return self._heads

    def head(self, id_: str):
        for h in self.heads():
            if h.id == id_:
                return h
        return None

    def superseded_by(self, id_: str) -> str:
        for h in self.heads():
            if id_ in h.l("supersedes"):
                return h.id
        return ""

    def content(self, head: SourceHead):
        """The source's text model. Only called after the gate has passed for it."""
        if head.id not in self._content:
            text = read_text(head.path)
            if text is None:
                raise Fail(EXIT_USAGE, {"error": "source-unknown", "source": head.id,
                                        "detail": "The source file could not be read."})
            self._content[head.id] = SourceText(Source(head.path, head.rel, text))
        return self._content[head.id]

    # observations

    def observations(self) -> list:
        if self._observations is None:
            found = []
            for folder in (INBOX, OBSERVATIONS):
                base = self.root / folder
                if not base.is_dir():
                    continue
                paths = sorted(base.glob("*.md")) if folder == INBOX else sorted(base.rglob("*.md"))
                for path in paths:
                    obs = load_observation(self.root, path, folder)
                    if obs is not None:
                        found.append(obs)
            self._observations = found
        return self._observations

    def observation(self, id_: str):
        for obs in self.observations():
            if obs["id"] == id_:
                return obs
        return None

    # numbering (R8) and known IDs

    def scan_texts(self):
        """(relative path, text) of every `*.md` the numbering scan reads (R8): never raw/,
        `_templates/`, hidden folders, a restricted source, or any source's content region."""
        restricted = self.index_restricted()
        skipped = (RAW_DIR, "_templates")
        for dirpath, dirnames, filenames in os.walk(str(self.root)):
            rel_dir = Path(dirpath).relative_to(self.root).as_posix()
            dirnames[:] = sorted(
                d for d in dirnames
                if not d.startswith(".") and (d if rel_dir == "." else f"{rel_dir}/{d}") not in skipped)
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                path = Path(dirpath) / name
                rel = path.relative_to(self.root).as_posix()
                if rel.startswith(RAW_DIR + "/"):
                    continue
                if rel.startswith(EXTRACTED_DIR + "/"):
                    if path.stem in restricted:
                        continue
                    text = read_text(path)
                    if text is None:
                        continue
                    yield rel, strip_content(text)
                    continue
                text = read_text(path)
                if text is not None:
                    yield rel, text

    def next_number(self) -> int:
        highest = 0
        for rel, text in self.scan_texts():
            m = re.match(r"^O-(\d{3,})$", Path(rel).stem)
            if m:
                highest = max(highest, int(m.group(1)))
            for m in O_MENTION.finditer(text):
                highest = max(highest, int(m.group(1)))
        return highest + 1

    def known_ids(self) -> set:
        known = {h.id for h in self.heads()}
        index = read_text(self.root / INDEX) or ""
        known |= set(re.findall(r"^\|\s*(S-\d{3,})\s*\|", index, re.M))
        for rel, text in self.scan_texts():
            stem = Path(rel).stem
            if ID_TOKEN.match(stem):
                known.add(stem)
            lines = text.split("\n")
            fm, _ = split_front_matter(lines)
            if fm is not None:
                value = parse_mapping(fm, 2)[0].get("id")
                if isinstance(value, str) and ID_TOKEN.match(value.strip()):
                    known.add(value.strip())
            for line in lines:
                m = STRICT_HEADING.match(line)
                if m:
                    known.add(f"{m.group(1)}-{m.group(2)}")
        return known

    # progress (R12)

    def progress(self) -> dict:
        text = read_text(self.root / PROGRESS)
        if not text:
            return {}
        try:
            data = json.loads(text)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}


def strip_content(text: str) -> str:
    """The text without the lines between the content markers."""
    out, inside = [], False
    for line in text.split("\n"):
        if line.strip() == CONTENT_START:
            inside = True
            continue
        if line.strip() == CONTENT_END:
            inside = False
            continue
        if not inside:
            out.append(line)
    return "\n".join(out)


def format_id(number: int) -> str:
    return f"O-{number:03d}"


# --- Observations as stored -------------------------------------------------------------------


def body_sections(lines: list, start: int) -> dict:
    """`## <name>` → list of lines below it, for the body of an observation file."""
    sections, current, in_fence = {}, None, False
    for line in lines[start:]:
        if line.startswith(("```", "~~~")):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def passage_lines(block: list) -> list:
    """The quoted lines of a `## Passage` block, with one `> ` prefix removed each."""
    out = []
    for line in block:
        s = line.rstrip()
        if s.startswith(">"):
            out.append(re.sub(r"^>\s?", "", s))
        elif s.strip() and out:
            out.append(s)
    while out and not out[-1].strip():
        out.pop()
    return out


def load_observation(root: Path, path: Path, folder: str):
    text = read_text(path)
    if text is None:
        return None
    lines = text.split("\n")
    fm, body = split_front_matter(lines)
    fields, errors = parse_mapping(fm, 2) if fm is not None else ({}, [])
    id_ = _str(fields.get("id")).strip()
    if not OBS_ID.match(id_) and not OBS_ID.match(path.stem):
        return None
    if fm is not None and _str(fields.get("type")).strip() not in ("", "observation"):
        return None
    sections = body_sections(lines, body if fm is not None else 0)
    claim = _one_line(" ".join(sections.get("Claim", [])))
    has_passage = "Passage" in sections
    plines = passage_lines(sections.get("Passage", []))
    return {
        "id": id_ or path.stem, "status": _str(fields.get("status")).strip(),
        "source": _str(fields.get("source")).strip(), "locator": _str(fields.get("locator")).strip(),
        "questions": as_list(fields.get("questions")), "claim": claim,
        "passage": " ".join(l.strip() for l in plines if l.strip()), "passage_lines": plines,
        "has_passage": has_passage, "folder": folder, "path": path,
        "rel": path.relative_to(root).as_posix(), "fields": fields, "fm_ok": fm is not None,
        "fm_errors": errors, "norm_passage": normalize_quote(plines), "norm_claim": norm_claim(claim),
    }


def norm_claim(text: str) -> str:
    return " ".join(_str(text).casefold().split()).rstrip(".").strip()


# --- The content model: units, tokens, tables -------------------------------------------------


class _Line(str):
    """A content line that remembers its 1-based line number (split_units keeps the object)."""

    n = 0


def _make_line(text: str, n: int) -> _Line:
    line = _Line(text)
    line.n = n
    return line


class Tok:
    __slots__ = ("word", "start", "line", "derived", "comment", "tracked", "table", "row")

    def __init__(self, word, line, derived, comment, tracked, table, row):
        self.word, self.line, self.derived, self.comment = word, line, derived, comment
        self.tracked, self.table, self.row = tracked, table, row
        self.start = 0


class Seg:
    """One content unit (page, heading section, ¶, turn, footnotes, comments) as tokens."""

    def __init__(self, unit, kind: str):
        self.locator, self.line, self.key, self.header = unit.locator, unit.line, unit.key, unit.header
        self.kind = kind
        self.tokens = []
        self.tables = []
        self.comments = {}
        self.callouts = []
        self.text = ""

    @property
    def turn(self):
        return self.key if self.kind == "turns" and isinstance(self.key, int) else None

    def finish(self) -> None:
        pos = 0
        for tok in self.tokens:
            tok.start = pos
            pos += len(tok.word) + 1
        self.text = " ".join(t.word for t in self.tokens)

    def span(self, lo: int, hi: int) -> tuple:
        """Character range of tokens [lo, hi) in `text`."""
        if lo >= hi:
            return (0, 0)
        return (self.tokens[lo].start, self.tokens[hi - 1].start + len(self.tokens[hi - 1].word))


def tracked_flags(text: str, state: bool) -> tuple:
    flags = [False] * len(text)
    i = 0
    while i < len(text):
        if text.startswith(("{++", "{--"), i):
            state = True
            for k in range(i, min(i + 3, len(text))):
                flags[k] = True
            i += 3
            continue
        if state and text.startswith(("++}", "--}"), i):
            for k in range(i, min(i + 3, len(text))):
                flags[k] = True
            state = False
            i += 3
            continue
        flags[i] = state
        i += 1
    return flags, state


ROW_WORD = re.compile(r"(?:\\\||[^\s|])+")
TEXT_WORD = re.compile(r"\S+")


def line_words(text: str, is_row: bool, state: bool = False) -> tuple:
    """[(word, tracked)] for one logical line; `**` dropped, table pipes dropped in rows."""
    flags, state = tracked_flags(text, state)
    words = []
    for m in (ROW_WORD if is_row else TEXT_WORD).finditer(text):
        word = m.group(0).replace("**", "")
        if word:
            words.append((word, any(flags[m.start():m.end()])))
    return words, state


def row_cells(text: str) -> list:
    return [" ".join(c.replace("**", "").split()) for c in CELL_SPLIT.split(text.strip().strip("|"))]


def logical_lines(body: list, default_line: int) -> list:
    """[(line number, text or None, callout)] with callout headers as boundaries (text None),
    `> ` prefixes removed, and the `was:` line of a corrected callout dropped."""
    out = []
    callout = None
    for raw in body:
        n = getattr(raw, "n", 0) or default_line
        s = raw.strip()
        m = CALLOUT.match(s)
        if m:
            kind, rest = m.group(1).lower(), m.group(2).strip()
            callout = {"kind": kind, "rest": rest, "line": n, "comment": None,
                       "derived": kind == "derived" or (kind == "corrected" and "derived" in rest)}
            if kind == "comment":
                parts = [p.strip() for p in rest.split(" · ")]
                if parts and parts[0].isdigit():
                    callout["comment"] = int(parts[0])
                callout["anchor"] = parts[-1] if len(parts) > 1 and parts[-1].startswith("§") else ""
            out.append((n, None, callout))
            continue
        if callout is not None and not s.startswith(">"):
            callout = None
        text = raw
        if callout is not None:
            text = re.sub(r"^\s*>\s?", "", raw)
            if callout["kind"] == "corrected" and text.startswith("was:"):
                continue
        elif s.startswith(">"):
            text = re.sub(r"^\s*>\s?", "", raw)
        out.append((n, text, callout))
    return out


def build_seg(unit, kind: str) -> Seg:
    seg = Seg(unit, kind)
    lines = logical_lines(unit.body, unit.line)
    state = False
    i = 0
    while i < len(lines):
        n, text, callout = lines[i]
        if text is None:
            seg.callouts.append(callout)
            if callout["kind"] == "comment" and callout["comment"] is not None:
                seg.comments[callout["comment"]] = {"anchor": callout.get("anchor", ""), "line": n,
                                                     "lo": len(seg.tokens), "hi": len(seg.tokens)}
            i += 1
            continue
        if text.strip().startswith("|"):
            # A table: consecutive row lines in the same callout (or none).
            j = i
            rows = []
            while j < len(lines) and lines[j][1] is not None and lines[j][2] is callout \
                    and lines[j][1].strip().startswith("|"):
                rows.append(lines[j])
                j += 1
            has_header = len(rows) >= 2 and TABLE_SEPARATOR.match(rows[1][1].strip()) is not None
            table = {"table": len(seg.tables) + 1, "line": rows[0][0], "rows": [],
                     "columns": row_cells(rows[0][1]) if has_header else []}
            seg.tables.append(table)
            data = rows[2:] if has_header else rows
            if has_header:
                state = add_tokens(seg, rows[0][1], rows[0][0], callout, state, (table["table"], 0), True)
            for rn, (ln, rtext, _) in enumerate(data, start=1):
                if TABLE_SEPARATOR.match(rtext.strip()):
                    continue
                lo = len(seg.tokens)
                state = add_tokens(seg, rtext, ln, callout, state, (table["table"], len(table["rows"]) + 1), True)
                table["rows"].append({"line": ln, "lo": lo, "hi": len(seg.tokens)})
            i = j
            continue
        state = add_tokens(seg, text, n, callout, state, None, False)
        i += 1
    seg.finish()
    return seg


def add_tokens(seg: Seg, text: str, n: int, callout, state: bool, table, is_row: bool) -> bool:
    words, state = line_words(text, is_row, state)
    comment = callout["comment"] if callout and callout["kind"] == "comment" else None
    derived = bool(callout and callout["derived"])
    for word, tracked in words:
        seg.tokens.append(Tok(word, n, derived, comment, tracked,
                              table[0] if table else None, table[1] if table else None))
    if comment is not None and comment in seg.comments:
        seg.comments[comment]["hi"] = len(seg.tokens)
    return state


def normalize_quote(lines) -> str:
    """The quote (or a stored passage) normalised as the source's units are (R5)."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    words = []
    for raw in lines:
        s = raw.strip()
        if CALLOUT.match(s):
            continue
        s = re.sub(r"^>\s?", "", s).strip()
        if s.startswith("|"):
            if TABLE_SEPARATOR.match(s):
                continue
            words += [w for w, _ in line_words(s, True)[0]]
        else:
            words += [w for w, _ in line_words(s, False)[0]]
    return " ".join(words)


def find_all(text: str, needle: str, lo: int = 0, hi=None) -> list:
    """Start offsets of `needle` in text[lo:hi] that don't cut a word at either end."""
    hi = len(text) if hi is None else hi
    found = []
    if not needle:
        return found
    start = text.find(needle, lo, hi)
    while start >= 0:
        end = start + len(needle)
        before_ok = start == lo or not (text[start - 1].isalnum() and needle[0].isalnum())
        after_ok = end == hi or not (text[end].isalnum() and needle[-1].isalnum())
        if before_ok and after_ok:
            found.append(start)
        start = text.find(needle, start + 1, hi)
    return found


def tokens_in(seg: Seg, start: int, end: int) -> list:
    return [t for t in seg.tokens if t.start < end and t.start + len(t.word) > start]


class SourceText:
    """An eligible source's content as units of tokens, with its outside sections normalised."""

    def __init__(self, src: Source):
        self.src = src
        self.kind = source_kind(src)
        first = src.content_first_line()
        lines = []
        for offset, line in enumerate(src.content_lines()):
            if line.strip() in UNIT_COMMENTS or not HTML_COMMENT.match(line):
                lines.append((first + offset, _make_line(line, first + offset)))
        self.segs = [build_seg(u, self.kind) for u in split_units(lines, self.kind)
                     if u.key != "pre" or any(l.strip() for l in u.body)]
        self.outside = {name: normalize_quote(src.section_lines(name))
                        for name in ("Context", "Description", "Speakers", "Uncertain passages")}
        self.names = {}
        rows = [l.strip() for l in src.section_lines("Speakers") if l.strip().startswith("|")]
        for row in rows[2:] if len(rows) >= 2 else []:
            cells = [c.strip() for c in CELL_SPLIT.split(row.strip("|"))]
            if cells and cells[0]:
                self.names[cells[0]] = confirmed_name(cells[1] if len(cells) > 1 else "")

    def pages(self) -> list:
        return [s.key for s in self.segs if self.kind == "pdf" and isinstance(s.key, int)]

    def speaker(self, seg: Seg) -> str:
        if seg.kind != "turns" or not seg.header:
            return ""
        label = seg.header[0]
        return self.names.get(label) or label

    def unit_locator(self, seg: Seg) -> str:
        return f"T{seg.key}" if seg.turn is not None else seg.locator


def confirmed_name(cell: str) -> str:
    value = re.sub(r"\s*\([^)]*\)\s*$", "", _one_line(cell))
    if value.lower() in ("", "-", "—", "not confirmed", "unconfirmed", "unknown"):
        return ""
    return value


# --- Locators (data-model §3) -----------------------------------------------------------------


def parse_locator(locator: str):
    """{unit, table, row, column, comment, anchor} or None when malformed."""
    parts = [p.strip() for p in re.split(r"\s*›\s*", _one_line(locator))]
    out = {"unit": parts[0], "table": None, "row": None, "column": None, "comment": None, "anchor": ""}
    if not parts[0]:
        return None
    rest = parts[1:]
    if rest:
        m = re.match(r"^table\s+(\d+)$", rest[0], re.I)
        if not m or len(rest) < 2:
            return None
        r = re.match(r"^row\s+(\d+)$", rest[1], re.I)
        if not r:
            return None
        out["table"], out["row"] = int(m.group(1)), int(r.group(1))
        if len(rest) > 2:
            out["column"] = SEP.join(rest[2:])
    c = re.match(r"^comment\s+(\d+)(?:\s*@\s*(.*))?$", out["unit"], re.I)
    if c:
        out["comment"], out["anchor"] = int(c.group(1)), _one_line(c.group(2) or "")
    return out


def unit_candidates(text: SourceText, unit: str) -> list:
    unit = _one_line(unit)
    t = re.match(r"^T\s?(\d+)$", unit)
    found = []
    for seg in text.segs:
        if seg.kind == "turns" and seg.turn is not None:
            if (t and int(t.group(1)) == seg.turn) or (seg.header and seg.header[1] == unit):
                found.append(seg)
        elif seg.locator == unit:
            found.append(seg)
    if not found and unit.startswith("§ "):
        para = re.match(r"^(.*\S)\s+¶\s*\d+$", unit)
        if para:
            found = [s for s in text.segs if s.locator == para.group(1)]
    return found


def resolve(text: SourceText, loc: dict):
    """[(seg, lo, hi, info)] token ranges the quote must lie in, or a (code, detail) refusal."""
    if loc["comment"] is not None:
        hits = []
        for seg in text.segs:
            c = seg.comments.get(loc["comment"])
            if c is None:
                continue
            if loc["anchor"] and _one_line(c["anchor"]) != loc["anchor"]:
                return ("locator-unknown", f"comment {loc['comment']} is anchored at {c['anchor'] or 'no heading'}")
            hits.append((seg, c["lo"], c["hi"], {"comment": True}))
        return hits or ("locator-unknown", f"no comment {loc['comment']} in this source")
    segs = unit_candidates(text, loc["unit"])
    if not segs:
        return ("locator-unknown", f"no unit {loc['unit']!r} in this source (see prepare's units)")
    if loc["table"] is None:
        return [(seg, 0, len(seg.tokens), {}) for seg in segs]
    hits = []
    reason = f"{loc['unit']} has no table {loc['table']}"
    for seg in segs:
        if loc["table"] > len(seg.tables):
            continue
        table = seg.tables[loc["table"] - 1]
        if loc["row"] < 1 or loc["row"] > len(table["rows"]):
            reason = f"table {loc['table']} at {loc['unit']} has {len(table['rows'])} data rows"
            continue
        if loc["column"] is not None:
            wanted = " ".join(loc["column"].replace("**", "").split()).casefold()
            if wanted not in [c.casefold() for c in table["columns"]]:
                reason = f"table {loc['table']} has no column {loc['column']!r}"
                continue
        row = table["rows"][loc["row"] - 1]
        hits.append((seg, row["lo"], row["hi"], {"row": True}))
    return hits or ("locator-unknown", reason)


def uncertain_hit(locator: str, units: list, entries: list) -> bool:
    """True when the locator (or one of the unit's names) equals or lies under an uncertain entry."""
    for entry in entries:
        e = _one_line(entry)
        if not e:
            continue
        if locator == e or locator.startswith(e + SEP):
            return True
        if any(u and (u == e or u.startswith(e + " > ")) for u in units):
            return True
    return False


def excluded_by(text: SourceText, loc: dict, seg, locator: str, entries: list) -> str:
    """The exclusion entry the locator falls in, or ""."""
    unit = _one_line(loc["unit"])
    anchor = loc["anchor"]
    for entry in entries:
        e = _one_line(entry)
        if not e:
            continue
        sp = re.match(r"^speaker:\s*(.+)$", e, re.I)
        if sp:
            who = sp.group(1).strip().casefold()
            if seg is not None and seg.kind == "turns" and seg.header:
                if who in (seg.header[0].casefold(), text.speaker(seg).casefold()):
                    return entry
            continue
        pr = re.match(r"^p\.\s*(\d+)\s*[–-]\s*(\d+)$", e)
        if pr:
            pm = re.match(r"^p\.\s*(\d+)$", unit)
            if pm and int(pr.group(1)) <= int(pm.group(1)) <= int(pr.group(2)):
                return entry
            continue
        for target in (unit, anchor):
            if target and (target == e or target.startswith(e + " > ")):
                return entry
        if locator == e or locator.startswith(e + SEP):
            return entry
    return ""


# --- Gates (R13, data-model §5) ---------------------------------------------------------------


def gate(eng: Engagement, source_id: str, confirmed: bool):
    """None, or (exit code, code, detail) for one source. Reads front matter only."""
    if eng.model_use == "unconfirmed":
        return (EXIT_POLICY, "policy-unconfirmed", UNCONFIRMED_MESSAGE)
    head = eng.head(source_id) if SOURCE_ID.match(source_id or "") else None
    if head is None:
        return (EXIT_USAGE, "source-unknown", f"no source {source_id!r} in {EXTRACTED_DIR}/")
    if head.restricted or head.content_removed:
        what = "its content was removed" if head.content_removed else "it is restricted"
        return (EXIT_POLICY, "source-restricted", f"{head.id} was not opened: {what}")
    if not head.readable:
        return (EXIT_USAGE, "source-unknown", f"{head.id}: the source file could not be read")
    if head.f("extraction_status") != "complete":
        return (EXIT_USAGE, "source-incomplete", f"{head.id} is still being extracted (/ingest)")
    if head.f("origin") == "llm-inference":
        return (EXIT_USAGE, "source-llm-inference", f"{head.id} has origin llm-inference")
    if head.f("status") in ("rejected", "superseded") and not confirmed:
        by = eng.superseded_by(head.id)
        detail = f"{head.id} is {head.f('status')}" + (f"; superseded by {by}" if by else "")
        return (EXIT_USAGE, "source-retired", detail + "; ask the consultant, then use --confirmed")
    return None


def gate_or_fail(eng: Engagement, source_id: str, confirmed: bool) -> SourceHead:
    refusal = gate(eng, source_id, confirmed)
    if refusal is not None:
        code, name, detail = refusal
        payload = {"refused": name, "source": source_id, "detail": detail}
        if name == "policy-unconfirmed":
            payload = {"error": name, "message": detail}
        if name == "source-retired":
            payload["superseded_by"] = eng.superseded_by(source_id)
        raise Fail(code, payload)
    return eng.head(source_id)


def source_cap(head: SourceHead) -> str:
    cap = head.f("confidence") if head.f("confidence") in LEVELS else "medium"
    if head.f("author_kind") == "ai-notetaker" and LEVELS[cap] > LEVELS["medium"]:
        cap = "medium"
    return cap


# --- Checking one draft (add) or one stored observation (verify) ------------------------------


class Check:
    def __init__(self):
        self.refusals = []  # (code, detail)
        self.warnings = []  # (code, detail, existing)
        self.computed = {}

    def refuse(self, code: str, detail: str) -> None:
        self.refusals.append((code, detail))

    def warn(self, code: str, detail: str, existing: str = "") -> None:
        self.warnings.append((code, detail, existing))


def check_quote(eng: Engagement, head: SourceHead, d: dict, chk: Check, steering_exclude=()) -> None:
    """Locator, quote, exclusion, computed fields and the cap, for a gated source."""
    locator = _one_line(d["locator"])
    quote_lines = d["quote_lines"]
    quote = normalize_quote(quote_lines)
    raw_quote = "\n".join(quote_lines)
    if any(e in raw_quote for e in ELLIPSES):
        chk.refuse("quote-not-found", "no ellipses: quote one contiguous passage")
        return
    loc = parse_locator(locator)
    if loc is None:
        chk.refuse("locator-unknown", f"malformed locator {locator!r} (see data-model §3)")
        return
    if len(quote.split()) < 3 and loc["table"] is None:
        chk.refuse("quote-too-short", "quote at least 3 words (a whole sentence is best)")
        return
    text = eng.content(head)
    hits = resolve(text, loc)
    if isinstance(hits, tuple):
        chk.refuse(*hits)
        return
    first_seg = hits[0][0] if hits else None
    if steering_exclude:
        entry = excluded_by(text, loc, first_seg, locator, steering_exclude)
        if entry:
            chk.refuse("excluded", f"{locator} lies in the excluded part {entry!r}")
            return
    match = None
    for seg, lo, hi, info in hits:
        a, b = seg.span(lo, hi)
        starts = find_all(seg.text, quote, a, b)
        if starts:
            match = (seg, starts[0], starts[0] + len(quote), info)
            break
    if match is None:
        elsewhere = ""
        for seg in text.segs:
            if find_all(seg.text, quote):
                elsewhere = text.unit_locator(seg)
                break
        if elsewhere and loc["table"] is not None and elsewhere == text.unit_locator(first_seg):
            chk.refuse("quote-not-found", f"the quote is in {elsewhere} but not in table {loc['table']} row {loc['row']}")
        elif elsewhere:
            chk.refuse("quote-not-found", f"the quote is at {elsewhere}, not at {locator}")
        elif any(quote and quote in v for v in text.outside.values()):
            where = next(k for k, v in text.outside.items() if quote in v)
            chk.refuse("quote-outside-content", f"the quote is in ## {where}, which is never cited")
        else:
            chk.refuse("quote-not-found", "not found word for word in the source's content; copy it exactly")
        return
    seg, start, end, info = match
    toks = tokens_in(seg, start, end)
    if loc["table"] is None and loc["comment"] is None and any(t.table is not None for t in toks):
        table = next(t.table for t in toks if t.table is not None)
        row = next((t.row for t in toks if t.row), 1)
        chk.refuse("table-locator-missing",
                   f"the quote is a table row: use {text.unit_locator(seg)} › table {table} › row {row}")
        return
    derived = any(t.derived for t in toks)
    if loc["table"] is not None:
        kind = "table-row"
    elif any(t.comment is not None for t in toks) or info.get("comment"):
        kind = "comment"
    elif any(t.tracked for t in toks):
        kind = "tracked-change"
    else:
        kind = "text"
    src = text.src
    cap = source_cap(head)
    names = [_one_line(loc["unit"]), loc["anchor"], seg.locator, text.unit_locator(seg)]
    if seg.kind == "turns" and seg.header and seg.header[1]:
        names.append(seg.header[1])
    uncertain = uncertain_hit(locator, names, head.l("uncertain_passages"))
    if uncertain:
        cap = "low"
    chk.computed.update({
        "origin": src.f("origin"), "derived": derived, "passage_kind": kind,
        "speaker": text.speaker(seg) if src.f("material") == "meeting-transcript" else "",
        "label": seg.header[0] if seg.kind == "turns" and seg.header else "",
        "cap": cap, "uncertain": uncertain,
    })
    confidence = _str(d.get("confidence")).strip()
    if confidence in LEVELS and LEVELS[confidence] > LEVELS[cap]:
        why = "an uncertain passage" if uncertain else (
            "AI note-taker notes" if head.f("author_kind") == "ai-notetaker" else "the source's confidence")
        chk.refuse("confidence-cap", f"at most {cap} here ({why})")


def check_wording(eng: Engagement, head: SourceHead, d: dict, chk: Check) -> None:
    """Leak, attribution and translation rules on the title and claim."""
    claim, title = d["claim"], d["title"]
    for name, value in (("title", title), ("claim", claim)):
        if eng.leaks(value):
            chk.refuse("real-name-leak", f"the real client name is in the {name}; use {eng.client_label}")
            break
    lower = claim.lower()
    material = head.f("material")
    computed = chk.computed
    kind = computed.get("passage_kind", "")
    if material == "meeting-transcript" and computed.get("label"):
        names = {computed.get("speaker", "").lower(), computed["label"].lower()} - {""}
        if not any(n in lower for n in names):
            chk.warn("attribution-missing", f"say who said it: {computed.get('speaker') or computed['label']} said …")
    if material == "meeting-notes":
        author = head.f("author").lower()
        if not ((author and author in lower) or "summary" in lower or "notes" in lower):
            chk.warn("summary-attribution-missing", "say it comes from a summary and whose: The summary by <author> reports …")
    if kind == "comment" and "comment" not in lower:
        chk.warn("kind-unstated", "say it is a reviewer comment: A reviewer comment by <author> says …")
    if kind == "tracked-change" and not ("tracked change" in lower or "unaccepted change" in lower):
        chk.warn("kind-unstated", "say it is an unaccepted tracked change")
    if d.get("translated") is True and not claim.rstrip().rstrip(".").endswith("(translated)"):
        chk.refuse("bad-value", "translated: true needs the claim to end with \"(translated)\"")


def check_questions(eng: Engagement, questions, chk: Check) -> None:
    known = eng.question_ids()
    for q in questions:
        if q not in known:
            chk.refuse("question-unknown", f"{q} is not in {QUESTIONS}")
            return
    for q in questions:
        if known[q]["status"] in ("superseded", "rejected"):
            chk.warn("question-retired", f"{q} is {known[q]['status']}")


def overlap(a: str, b: str) -> bool:
    """One normalised passage contains the other, or they share ≥ 50% of words in order."""
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    wa, wb = a.split(), b.split()
    shared = sum(block.size for block in SequenceMatcher(None, wa, wb, autojunk=False).get_matching_blocks())
    return shared >= 0.5 * min(len(wa), len(wb))


# --- Writing observations from the engagement's template (Skill Contract 4) -------------------


def template_keys(eng: Engagement) -> list:
    """[(key, raw value text)] from `_templates/observation.md`, in order; exit 6 if outdated."""
    text = read_text(eng.root / TEMPLATE)
    keys = []
    if text is not None:
        fm, _ = split_front_matter(text.split("\n"))
        for line in fm or []:
            m = KEY_LINE.match(line)
            if m:
                keys.append((m.group(1), m.group(2) or ""))
    missing = [k for k in SKILL_FIELDS if k not in {key for key, _ in keys}]
    if text is None or missing:
        raise Fail(EXIT_USAGE, {"error": "template-outdated", "missing": missing if text is not None else list(SKILL_FIELDS),
                                "message": "Run `cairn refresh` to update _templates/observation.md."})
    return keys


def _render(key: str, value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(json.dumps(_str(v), ensure_ascii=False) for v in value) + "]"
    s = _str(value)
    if key in BARE_VALUES and re.match(r"^[a-z][a-z-]*$", s):
        return s
    return json.dumps(s, ensure_ascii=False)


def _keep(raw: str) -> str:
    """A template value the skill doesn't set, without its trailing comment."""
    value, error = parse_value(raw)
    if error:
        return raw.split(" #")[0].strip()
    if isinstance(value, list):
        return _render("", value)
    stripped = raw.strip()
    if stripped[:1] in "\"'":
        return json.dumps(value, ensure_ascii=False)
    return value


def render_observation(keys: list, fields: dict, claim: str, quote_lines: list) -> str:
    lines = ["---"]
    for key, raw in keys:
        lines.append(f"{key}: {_render(key, fields[key]) if key in fields else _keep(raw)}")
    lines += ["---", "", "## Claim", "", claim, "", "## Passage", ""]
    lines += [("> " + l) if l else ">" for l in quote_lines]
    return "\n".join(lines) + "\n"


def stored_quote_lines(quote: str) -> list:
    """The quote as it will be stored: callout headers dropped, one `> ` prefix removed."""
    out = []
    for line in _str(quote).replace("\r\n", "\n").split("\n"):
        s = line.rstrip()
        if CALLOUT.match(s.strip()):
            continue
        if s.lstrip().startswith(">"):
            s = re.sub(r"^\s*>\s?", "", s)
        out.append(s)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


# --- Commands ---------------------------------------------------------------------------------


def source_entry(eng: Engagement, head: SourceHead, counts: Counter, progress: dict) -> dict:
    reason = ""
    if head.restricted:
        reason = "restricted"
    elif head.content_removed:
        reason = "content-removed"
    elif head.f("extraction_status") != "complete":
        reason = "in-progress"
    elif head.f("origin") == "llm-inference":
        reason = "llm-inference"
    elif head.f("status") in ("rejected", "superseded"):
        reason = "retired"
    entry = progress.get(head.id)
    return {
        "id": head.id, "title": head.f("title"), "material": head.f("material"), "status": head.f("status"),
        "extraction_status": head.f("extraction_status"), "restricted": head.restricted,
        "content_removed": head.content_removed, "observations": counts.get(head.id, 0),
        "progress": entry if isinstance(entry, dict) else None, "eligible": reason == "",
        "reason": reason, "superseded_by": eng.superseded_by(head.id),
    }


def cmd_status(eng: Engagement, args) -> tuple:
    eng.require_policy()
    heads = eng.heads()
    if args.ids:
        known = {h.id for h in heads}
        unknown = [i for i in args.ids if i not in known]
        if unknown:
            raise Fail(EXIT_USAGE, {"error": "source-unknown", "ids": unknown})
        heads = [h for h in heads if h.id in set(args.ids)]
    counts = Counter(o["source"] for o in eng.observations())
    progress = eng.progress()
    return EXIT_OK, {
        "engagement_name": eng.engagement_name, "client_label": eng.client_label,
        "uses_code_name": eng.uses_code_name, "model_use": eng.model_use,
        "questions": eng.questions(), "next_id": format_id(eng.next_number()),
        "sources": [source_entry(eng, h, counts, progress) for h in heads],
    }


def existing_for(eng: Engagement, source_id: str) -> list:
    return [{"id": o["id"], "status": o["status"], "locator": o["locator"], "questions": o["questions"],
             "claim": o["claim"], "passage": o["passage"], "folder": o["folder"]}
            for o in eng.observations() if o["source"] == source_id]


def cmd_prepare(eng: Engagement, args) -> tuple:
    head = gate_or_fail(eng, args.id, args.confirmed)
    text = eng.content(head)
    src = text.src
    units, tables, derived = [], [], []
    for seg in text.segs:
        if seg.kind == "turns" and seg.turn is not None:
            units.append({"locator": f"T{seg.turn}", "timestamp": seg.header[1] or "",
                          "speaker": text.speaker(seg), "line": seg.line})
        else:
            units.append({"locator": seg.locator, "line": seg.line})
        for n, c in sorted(seg.comments.items()):
            units.append({"locator": f"comment {n} @ {c['anchor']}" if c["anchor"] else f"comment {n}",
                          "line": c["line"]})
        for t in seg.tables:
            tables.append({"unit": text.unit_locator(seg), "table": t["table"], "rows": len(t["rows"]),
                           "columns": t["columns"], "line": t["line"]})
        for c in seg.callouts:
            if c["derived"]:
                kind = c["rest"].split()[0] if c["kind"] == "derived" and c["rest"] else c["kind"]
                derived.append({"unit": text.unit_locator(seg), "kind": kind, "line": c["line"]})
    first = src.content_first_line()
    return EXIT_OK, {
        "source": {
            "id": head.id, "material": src.f("material"), "origin": src.f("origin"),
            "confidence": src.f("confidence"), "author_kind": src.f("author_kind"), "author": src.f("author"),
            "status": src.f("status"), "source_not_approved": src.f("status") == "proposed",
            "fidelity": src.f("fidelity"), "uncertain_passages": src.l("uncertain_passages"),
            "path": head.rel, "content_lines": [first, first + max(len(src.content_lines()) - 1, 0)],
        },
        "cap": source_cap(head),
        "units": units, "tables": tables, "derived": derived,
        "speakers": [{"label": label, "name": name} for label, name in text.names.items()],
        "existing": existing_for(eng, head.id),
        "progress": eng.progress().get(head.id),
        "superseded_by": eng.superseded_by(head.id),
    }


def read_drafts(eng: Engagement, arg: str) -> dict:
    path = Path(arg)
    if not path.is_absolute() and not path.exists():
        path = eng.root / arg
    text = read_text(path)
    if text is None:
        raise Fail(EXIT_USAGE, {"error": "drafts-unreadable", "detail": f"cannot read {arg}"})
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise Fail(EXIT_USAGE, {"error": "drafts-unreadable", "detail": f"not JSON: {exc}"})
    if not isinstance(data, dict) or not isinstance(data.get("drafts", []), list):
        raise Fail(EXIT_USAGE, {"error": "drafts-unreadable", "detail": "expected {\"steering\": {…}, \"drafts\": [ … ]}"})
    steering = data.get("steering") or {}
    if not isinstance(steering, dict):
        raise Fail(EXIT_USAGE, {"error": "drafts-unreadable", "detail": "steering must be an object"})
    focus = steering.get("focus", [])
    exclude = steering.get("exclude", [])
    perspective = steering.get("perspective", "")
    if not (isinstance(focus, list) and all(isinstance(q, str) for q in focus)
            and isinstance(exclude, list) and all(isinstance(e, str) for e in exclude)
            and isinstance(perspective, str)):
        raise Fail(EXIT_USAGE, {"error": "drafts-unreadable",
                                "detail": "steering: focus and exclude are lists of strings, perspective a string"})
    if not all(isinstance(d, dict) for d in data.get("drafts", [])):
        raise Fail(EXIT_USAGE, {"error": "drafts-unreadable", "detail": "every draft must be an object"})
    return {"steering": {"focus": focus, "exclude": exclude, "perspective": perspective},
            "drafts": data.get("drafts", [])}


def draft_fields(d: dict) -> tuple:
    """(clean draft, refusal or None) for the required-field and value checks."""
    clean = {k: _one_line(d.get(k)) for k in DRAFT_REQUIRED if k != "quote"}
    clean["quote_lines"] = stored_quote_lines(d.get("quote"))
    missing = [k for k in DRAFT_REQUIRED if not (clean["quote_lines"] if k == "quote" else clean[k])]
    if missing:
        return clean, ("missing-field", "empty or missing: " + ", ".join(missing))
    questions = d.get("questions", [])
    if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
        return clean, ("bad-value", "questions must be a list of Q-IDs")
    clean["questions"] = [q.strip() for q in questions]
    translated = d.get("translated", False)
    if not isinstance(translated, bool):
        return clean, ("bad-value", "translated must be true or false")
    clean["translated"] = translated
    accept = d.get("accept_warnings", [])
    if not isinstance(accept, list) or not all(isinstance(a, str) for a in accept):
        return clean, ("bad-value", "accept_warnings must be a list of warning codes")
    clean["accept"] = accept
    if clean["confidence"] not in LEVELS:
        return clean, ("bad-value", f"confidence must be high, medium or low, not {clean['confidence']!r}")
    if len(clean["title"]) > TITLE_MAX:
        return clean, ("bad-value", f"title is {len(clean['title'])} characters; at most {TITLE_MAX}")
    if not SOURCE_ID.match(clean["source"]):
        return clean, ("bad-value", f"source must be an S-ID, not {clean['source']!r}")
    return clean, None


def cmd_add(eng: Engagement, args) -> tuple:
    # First pass, before any write: the policy and every cited source's gate (R13).
    if eng.model_use == "unconfirmed":
        raise Fail(EXIT_POLICY, {"refused": "policy-unconfirmed", "message": UNCONFIRMED_MESSAGE,
                                 "detail": "Nothing was written."})
    batch = read_drafts(eng, args.drafts)
    steering, drafts = batch["steering"], batch["drafts"]
    known_q = eng.question_ids()
    unknown_focus = [q for q in steering["focus"] if q not in known_q]
    if unknown_focus:
        raise Fail(EXIT_USAGE, {"error": "question-unknown", "ids": unknown_focus,
                                "detail": "steering.focus names questions that don't exist. Nothing was written."})
    gated = {}
    for d in drafts:
        sid = _one_line(d.get("source"))
        if not sid or sid in gated:
            continue
        refusal = gate(eng, sid, args.confirmed)
        if refusal is not None and refusal[0] == EXIT_POLICY:
            raise Fail(EXIT_POLICY, {"refused": refusal[1], "source": sid, "detail": "Nothing was written."})
        gated[sid] = refusal
    keys = template_keys(eng)
    number = eng.next_number()
    records = [o for o in eng.observations()]
    written, refused, warnings, not_approved = [], [], [], []
    for index, d in enumerate(drafts):
        clean, problem = draft_fields(d)
        if problem:
            refused.append({"index": index, "code": problem[0], "detail": problem[1]})
            continue
        refusal = gated.get(clean["source"])
        if refusal is not None:
            refused.append({"index": index, "code": refusal[1], "detail": refusal[2]})
            continue
        head = eng.head(clean["source"])
        chk = Check()
        check_questions(eng, clean["questions"], chk)
        if not chk.refusals and steering["focus"] and not set(clean["questions"]) & set(steering["focus"]):
            chk.refuse("off-focus", "tag it with a focus question, or drop it: " + ", ".join(steering["focus"]))
        if not chk.refusals:
            check_quote(eng, head, clean, chk, steering["exclude"])
        if not chk.refusals:
            check_wording(eng, head, clean, chk)
        norm_q = normalize_quote(clean["quote_lines"])
        claim_n = norm_claim(clean["claim"])
        if not chk.refusals:
            same = [o for o in records if o["source"] == clean["source"]
                    and o["norm_passage"] == norm_q and o["norm_claim"] == claim_n]
            if same:
                rejected = [o for o in same if o["status"] == "rejected"]
                if rejected:
                    chk.refuse("previously-rejected", f"the consultant rejected this claim as {rejected[0]['id']}")
                else:
                    chk.refuse("duplicate", f"already recorded as {same[0]['id']}")
        if not chk.refusals:
            for o in records:
                if o["source"] == clean["source"] and overlap(o["norm_passage"], norm_q):
                    chk.warn("same-passage", f"{o['id']} quotes an overlapping passage; keep this only for a different claim", o["id"])
                    break
        if chk.refusals:
            code, detail = chk.refusals[0]
            refused.append({"index": index, "code": code, "detail": detail})
            continue
        unaccepted = [w for w in chk.warnings if w[0] not in clean["accept"]]
        if unaccepted:
            code, detail, existing = unaccepted[0]
            entry = {"index": index, "code": code, "detail": "warning not accepted: " + detail}
            if existing:
                entry["existing"] = existing
            refused.append(entry)
            continue
        for code, detail, existing in chk.warnings:
            entry = {"index": index, "code": code, "detail": detail}
            if existing:
                entry["existing"] = existing
            warnings.append(entry)
        computed = chk.computed
        reason = clean["confidence_reason"]
        if computed["uncertain"] and clean["confidence"] == "low" and "uncertain" not in reason.lower():
            reason = UNCERTAIN_PREFIX + reason
        id_ = format_id(number)
        fields = {
            "id": id_, "type": "observation", "title": clean["title"], "status": "proposed",
            "origin": computed["origin"], "confidence": clean["confidence"], "confidence_reason": reason,
            "inference_confirmed": False, "audience": "internal", "supports": [], "contradicts": [],
            "derived_from": [], "supersedes": [], "clarifies": [], "change_reason": "", "change_trigger": "",
            "created": _today(), "source": clean["source"], "locator": clean["locator"],
            "questions": clean["questions"], "derived": computed["derived"], "speaker": computed["speaker"],
            "passage_kind": computed["passage_kind"], "translated": clean["translated"],
        }
        if not args.dry_run:
            path = eng.root / INBOX / f"{id_}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                raise Fail(EXIT_USAGE, {"error": "id-taken", "id": id_, "detail": "the file already exists; nothing more was written",
                                        "written": written})
            atomic_write(path, render_observation(keys, fields, clean["claim"], clean["quote_lines"]))
        number += 1
        records.append({"id": id_, "status": "proposed", "source": clean["source"], "norm_passage": norm_q,
                        "norm_claim": claim_n})
        if head.f("status") == "proposed" and head.id not in not_approved:
            not_approved.append(head.id)
        written.append({"id": id_, "title": clean["title"], "source": clean["source"], "locator": clean["locator"],
                        "questions": clean["questions"], "derived": computed["derived"],
                        "confidence": clean["confidence"], "passage_kind": computed["passage_kind"],
                        "speaker": computed["speaker"]})
    return EXIT_OK, {"written": written, "refused": refused, "warnings": warnings,
                     "next_id": format_id(number), "dry_run": bool(args.dry_run),
                     "steering": steering, "sources_not_approved": not_approved}


def cmd_progress(eng: Engagement, args) -> tuple:
    head = gate_or_fail(eng, args.id, True)
    entry = {"state": "done" if args.done else "stopped"}
    if args.stopped_at:
        loc = parse_locator(args.stopped_at)
        if loc is None or not unit_candidates(eng.content(head), loc["unit"]):
            raise Fail(EXIT_USAGE, {"error": "locator-unknown", "detail": f"no unit {args.stopped_at!r} in {head.id}"})
        entry["stopped_at"] = _one_line(args.stopped_at)
    if args.steering_from:
        entry["steering"] = read_drafts(eng, args.steering_from)["steering"]
    entry["updated"] = _today()
    data = eng.progress()
    data[head.id] = entry
    path = eng.root / PROGRESS
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return EXIT_OK, {"progress": {head.id: entry}}


def cmd_tag(eng: Engagement, args) -> tuple:
    eng.require_policy()
    obs = eng.observation(args.id)
    if obs is None:
        raise Fail(EXIT_USAGE, {"error": "observation-unknown", "id": args.id})
    known = eng.question_ids()
    unknown = [q for q in args.questions if q not in known]
    if unknown:
        raise Fail(EXIT_USAGE, {"error": "question-unknown", "ids": unknown})
    data = obs["path"].read_bytes().decode("utf-8")
    lines = data.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise Fail(EXIT_USAGE, {"error": "front-matter-unreadable", "id": args.id})
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    at = next((i for i in range(1, end or 0) if re.match(r"^questions:", lines[i])), None)
    if end is None or at is None:
        raise Fail(EXIT_USAGE, {"error": "bad-value", "id": args.id, "detail": "no `questions:` line in the front matter"})
    line = lines[at]
    newline = line[len(line.rstrip("\r\n")):]
    m = re.match(r"^questions:(\s*)(\[[^\]]*\])(.*)$", line.rstrip("\r\n"))
    if not m:
        raise Fail(EXIT_USAGE, {"error": "bad-value", "id": args.id,
                                "detail": "questions must be an inline list, e.g. questions: [\"Q-001\"]"})
    current, error = parse_value(m.group(2))
    current = as_list(current) if not error else []
    added = []
    for q in args.questions:
        if q not in current and q not in added:
            added.append(q)
    if not added:
        return EXIT_OK, {"tagged": [], "unchanged": [args.id]}
    value = "[" + ", ".join(json.dumps(q) for q in current + added) + "]"
    lines[at] = f"questions:{m.group(1) or ' '}{value}{m.group(3)}{newline}"
    atomic_write(obs["path"], "".join(lines))
    log = eng.root / CHANGELOG
    text = read_text(log) or ""
    entry = f"{_today()} · {args.id} · tag · added {', '.join(added)} · -"
    log.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(log, append_changelog(text, entry))
    return EXIT_OK, {"tagged": [{"id": args.id, "added": added}], "unchanged": []}


def verify_one(eng: Engagement, obs: dict, known_ids: set) -> tuple:
    problems, warnings = [], []
    f = obs["fields"]
    id_, rel = obs["id"], obs["rel"]

    def get(key):
        return _str(f.get(key)).strip()

    if not obs["fm_ok"]:
        return [_p("missing-field", id_, rel, "no front matter")], warnings
    for n, error in obs["fm_errors"]:
        problems.append(_p("bad-value", id_, rel, f"front matter line {n}: {error}"))
    missing = [k for k in STORED_REQUIRED if not get(k)]
    if missing:
        problems.append(_p("missing-field", id_, rel, "empty or missing: " + ", ".join(missing)))
    if get("status") not in STATUSES:
        problems.append(_p("bad-value", id_, rel, f"status: {get('status')!r}"))
    if get("confidence") and get("confidence") not in LEVELS:
        problems.append(_p("bad-value", id_, rel, f"confidence: {get('confidence')!r}"))
    if get("passage_kind") not in PASSAGE_KINDS:
        problems.append(_p("bad-value", id_, rel, f"passage_kind: {get('passage_kind')!r}"))
    if get("origin") == "llm-inference":
        problems.append(_p("bad-value", id_, rel, "origin llm-inference: a skill-written observation is never inferred"))
    if len(_one_line(f.get("title"))) > TITLE_MAX:
        problems.append(_p("bad-value", id_, rel, f"title is longer than {TITLE_MAX} characters"))
    audience = get("audience")
    if audience not in AUDIENCES:
        problems.append(_p("status-invalid", id_, rel, f"audience: {audience!r}"))
    elif get("status") == "proposed" and audience != "internal":
        problems.append(_p("client-ready", id_, rel, "a proposed observation stays internal"))
    for key in LINK_FIELDS:
        for target in as_list(f.get(key)):
            if target not in known_ids:
                problems.append(_p("broken-link", id_, rel, f"{key}: {target} does not exist"))
    source = get("source")
    if source and source not in known_ids:
        problems.append(_p("broken-link", id_, rel, f"source: {source} does not exist"))
    known_q = eng.question_ids()
    for q in obs["questions"]:
        if q not in known_q:
            problems.append(_p("question-unknown", id_, rel, f"{q} is not in {QUESTIONS}"))
    for key in ("title",):
        if eng.leaks(get(key)):
            problems.append(_p("real-name-leak", id_, rel, f"the real client name is in the {key}"))
    if eng.leaks(obs["claim"]):
        problems.append(_p("real-name-leak", id_, rel, "the real client name is in the claim"))
    if not obs["has_passage"]:
        warnings.append(_p("passage-missing", id_, rel, "no ## Passage (hand-written observations may omit it)"))
        return problems, warnings
    if missing or source not in known_ids:
        return problems, warnings
    if eng.model_use == "unconfirmed":
        warnings.append(_p("policy-unconfirmed", id_, rel, "model use is unconfirmed; the source was not opened"))
        return problems, warnings
    refusal = gate(eng, source, True)
    if refusal is not None:
        problems.append(_p(refusal[1], id_, rel, refusal[2]))
        return problems, warnings
    head = eng.head(source)
    draft = {"locator": get("locator"), "quote_lines": obs["passage_lines"], "claim": obs["claim"],
             "title": _one_line(f.get("title")), "confidence": get("confidence"),
             "translated": _bool(f.get("translated"))}
    chk = Check()
    check_quote(eng, head, draft, chk)
    if not chk.refusals:
        check_wording(eng, head, draft, chk)
        c = chk.computed
        if _bool(f.get("derived")) != c["derived"]:
            chk.refuse("derived-flag", f"derived is {str(_bool(f.get('derived'))).lower()} but the passage "
                                       f"{'is' if c['derived'] else 'is not'} in derived content")
        if get("origin") and get("origin") != c["origin"]:
            chk.refuse("bad-value", f"origin {get('origin')!r} differs from the source's {c['origin']!r}")
        if get("speaker") and get("speaker") != c["speaker"]:
            chk.refuse("bad-value", f"speaker {get('speaker')!r} differs from the source's {c['speaker']!r}")
        if get("passage_kind") and get("passage_kind") != c["passage_kind"]:
            chk.refuse("bad-value", f"passage_kind {get('passage_kind')!r}, but the passage is {c['passage_kind']}")
        if c["uncertain"] and "uncertain" not in get("confidence_reason").lower():
            chk.refuse("confidence-cap", "under an uncertain passage the reason must say so")
    for code, detail in chk.refusals:
        if code != "real-name-leak":  # already reported above
            problems.append(_p(code, id_, rel, detail))
    for code, detail, _ in chk.warnings:
        if code != "question-retired":
            warnings.append(_p(code, id_, rel, detail))
    return problems, warnings


def cmd_verify(eng: Engagement, args) -> tuple:
    observations = eng.observations()
    if args.ids:
        found = {o["id"] for o in observations}
        unknown = [i for i in args.ids if i not in found]
        if unknown:
            raise Fail(EXIT_USAGE, {"error": "observation-unknown", "ids": unknown})
        observations = [o for o in observations if o["id"] in set(args.ids)]
    known_ids = eng.known_ids()
    problems, warnings = [], []
    seen = {}
    for obs in eng.observations():
        seen.setdefault(obs["id"], []).append(obs["rel"])
    for obs in observations:
        if len(seen.get(obs["id"], [])) > 1:
            problems.append(_p("bad-value", obs["id"], obs["rel"], "the same ID is used by " + ", ".join(seen[obs["id"]])))
        p, w = verify_one(eng, obs, known_ids)
        problems += p
        warnings += w
    result = {"checked": len(observations), "problems": problems, "warnings": warnings}
    return (EXIT_PROBLEMS if problems else EXIT_OK), result


# --- Main -------------------------------------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="observe.py", description="Helper for the Cairn `extract-observations` skill.")
    parser.add_argument("--root", help="engagement folder (skips discovery)")
    parser.add_argument("--version", action="version", version=f"observe.py {SCRIPT_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    status = sub.add_parser("status", help="engagement facts, questions, sources and the next ID")
    status.add_argument("ids", nargs="*", metavar="S-ID")
    prepare = sub.add_parser("prepare", help="gate one source and outline it (no source text)")
    prepare.add_argument("id", metavar="S-ID")
    prepare.add_argument("--confirmed", action="store_true")
    add = sub.add_parser("add", help="check drafts and write the accepted ones to _inbox/")
    add.add_argument("drafts", metavar="DRAFTS")
    add.add_argument("--dry-run", action="store_true")
    add.add_argument("--confirmed", action="store_true")
    progress = sub.add_parser("progress", help="record where a long source stopped, or that it is done")
    progress.add_argument("id", metavar="S-ID")
    when = progress.add_mutually_exclusive_group(required=True)
    when.add_argument("--stopped-at", metavar="LOCATOR")
    when.add_argument("--done", action="store_true")
    progress.add_argument("--steering-from", metavar="DRAFTS")
    tag = sub.add_parser("tag", help="add question tags to an existing observation (logged)")
    tag.add_argument("id", metavar="O-ID")
    tag.add_argument("questions", nargs="+", metavar="Q-ID")
    verify = sub.add_parser("verify", help="re-check stored observations; exit 1 when there are problems")
    verify.add_argument("ids", nargs="*", metavar="O-ID")
    return parser


COMMANDS = {
    "status": cmd_status, "prepare": cmd_prepare, "add": cmd_add, "progress": cmd_progress,
    "tag": cmd_tag, "verify": cmd_verify,
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
