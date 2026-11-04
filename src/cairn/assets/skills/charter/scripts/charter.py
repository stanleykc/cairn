#!/usr/bin/env python3
"""Helper for the `charter` skill: engagement facts, next IDs, checks, links, model-use policy.

    python3 charter.py [--root PATH] status
    python3 charter.py [--root PATH] check
    python3 charter.py [--root PATH] refs ID [ID ...]
    python3 charter.py [--root PATH] model-use --set {allowed,restricted,unconfirmed} [--notes TEXT]

Contract: specs/002-charter-skill/contracts/charter-script.md. Python 3.9+, standard library
only, no network. It never opens anything under `10-sources/`, never prints the text of
objects outside `00-charter/`, and never prints the real client name when a code name is
in use. It does not import `cairn`: each engagement runs the copy pinned to its own
framework version.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

SCRIPT_VERSION = "0.2.0"

EXIT_OK, EXIT_PROBLEMS, EXIT_NO_ENGAGEMENT, EXIT_USAGE = 0, 1, 2, 3

NOT_IN_ENGAGEMENT = (
    "Not inside a Cairn engagement. Create one with `cairn init`, then run `charter` "
    "from inside it."
)

# The canonical layout minus `10-sources/` (and its subfolders) and `_templates/` (R9).
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

CHANGELOG = "60-log/changelog.md"
SCOPE = "00-charter/scope.md"
STAKEHOLDERS = "00-charter/stakeholders.md"
LENSES = "00-charter/lenses.md"
# file → (type, prefix)
COLLECTIONS = {
    "00-charter/questions.md": ("question", "Q"),
    "00-charter/hypotheses.md": ("hypothesis", "H"),
    "00-charter/assumptions.md": ("assumption", "A"),
}
HOLDS_PREFIX = {"question": "Q", "hypothesis": "H", "assumption": "A"}

STANDARD_FIELDS = (
    "id", "type", "title", "status", "origin", "confidence", "confidence_reason",
    "inference_confirmed", "audience", "supports", "contradicts", "derived_from",
    "supersedes", "clarifies", "created",
)
TYPE_FIELDS = {
    "question": ("priority", "raised_by", "hypotheses"),
    "hypothesis": ("question", "supported_by", "contradicted_by"),
    "assumption": ("basis", "questions"),
}
LINK_FIELDS = (
    "supports", "contradicts", "derived_from", "supersedes", "clarifies",
    "hypotheses", "questions", "supported_by", "contradicted_by",
)
ALLOWED = {
    "status": ("proposed", "active", "superseded", "rejected"),
    "origin": ("client-document", "interview-meeting", "external-research",
               "prior-engagement", "llm-inference", "consultant-note"),
    "confidence": ("high", "medium", "low"),
    "audience": ("internal", "client-ready"),
}
PRIORITIES = ("high", "medium", "low")
TRIGGERS = ("new-evidence", "client-feedback", "rethinking")
LIVE = ("proposed", "active")
MODEL_USE_VALUES = ("allowed", "restricted", "unconfirmed")

SCOPE_SECTIONS = ("Objectives", "In scope", "Out of scope", "Deliverables", "Timeline", "Constraints")
# Seed guidance sentences that count as "empty", from both framework versions.
SEED_GUIDANCE_0_1 = {
    "Objectives": "What the client needs from this engagement, in a few bullet points.",
    "Deliverables": "What will be handed to the client, and in what form.",
    "Timeline": "Key dates: kick-off, interviews, readouts, final delivery.",
}
SEED_GUIDANCE_0_2 = {
    **SEED_GUIDANCE_0_1,
    "In scope": "What the engagement covers, in a few bullet points.",
    "Out of scope": "What the engagement does not cover, in a few bullet points.",
    "Constraints": "One bullet each, starting with **Budget**, **Timeline**, **Technology**, "
                   "**Politics** or **Other**.",
}

ID_TOKEN = re.compile(r"^[A-Z]-\d{3,}$")
QHA_TOKEN = re.compile(r"^[QHA]-\d{3,}$")
SOURCE_ID = re.compile(r"\bS-\d{3,}\b")
STRICT_HEADING = re.compile(r"^## ([A-Z])-(\d{3,}): (\S.*)$")
LOOSE_HEADING = re.compile(r"^## ([A-Z]{1,3}-[^\s:]*)")
YAML_FENCE = re.compile(r"^```\s*ya?ml\s*$")
KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")
LIST_ITEM = re.compile(r"^\s*-(?:\s+(.*))?$")


class Fail(Exception):
    """Stop with an exit code and a message on stderr."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# --- Parsing (R4) -------------------------------------------------------------


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


# --- The engagement ------------------------------------------------------------


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
    """The engagement root (R5): --root, else walk up from cwd, else the script's own engagement."""
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


def _walk_roots() -> list:
    """Top-level content folders; their subfolders are reached by walking."""
    return [f for f in CONTENT_FOLDERS if f.rpartition("/")[0] not in CONTENT_FOLDERS]


class Engagement:
    def __init__(self, root: Path):
        self.root = root
        text = read_text(root / "engagement.md")
        lines = (text or "").splitlines()
        fm_lines, _ = split_front_matter(lines)
        if text is None or fm_lines is None:
            raise Fail(EXIT_NO_ENGAGEMENT, "The engagement record (engagement.md) could not be read.")
        self.record, _ = parse_mapping(fm_lines, 2)
        # The real client name is kept here only, for the leak check and output redaction.
        self._client = _str(self.record.get("client")).strip()
        self.code_name = _str(self.record.get("client_code_name")).strip()
        self.texts = self._scan()
        self.parsed = {rel: parse_file(self.texts[rel], rel) for rel in COLLECTIONS if rel in self.texts}

    def _scan(self) -> dict:
        """Every `*.md` under the content folders, by engagement-relative path (never 10-sources/)."""
        texts = {}
        for top in _walk_roots():
            base = self.root / top
            if not base.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
                for name in sorted(filenames):
                    if not name.endswith(".md"):
                        continue
                    path = Path(dirpath) / name
                    text = read_text(path)
                    if text is not None:
                        texts[path.relative_to(self.root).as_posix()] = text
        return texts

    @property
    def uses_code_name(self) -> bool:
        return bool(self.code_name)

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
        """Remove the real client name from anything printed, when a code name is in use (R7)."""
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

    # --- charter content ---

    def entries(self) -> list:
        result = []
        for rel in COLLECTIONS:
            if rel in self.parsed:
                result += self.parsed[rel]["entries"]
        return result

    def next_ids(self) -> dict:
        result = {}
        for prefix in ("Q", "H", "A"):
            token = re.compile(rf"\b{prefix}-(\d{{3,}})\b")
            highest = 0
            for text in self.texts.values():
                for match in token.finditer(text):
                    highest = max(highest, int(match.group(1)))
            result[prefix] = f"{prefix}-{highest + 1:03d}"
        return result

    def scope(self) -> dict:
        text = self.texts.get(SCOPE)
        if text is None:
            return {"front": {}, "sections": {s: "missing" for s in SCOPE_SECTIONS}}
        parsed = parse_file(text, SCOPE)
        return {"front": parsed["front"], "sections": scope_sections(parsed["lines"], parsed["body"])}

    def charter_block(self) -> dict:
        scope = self.scope()
        front = scope["front"]
        charter_status = _str(front.get("charter_status")) or "draft"
        filled = any(v == "filled" for v in scope["sections"].values())
        if not self.entries() and not filled:
            state = "empty"
        else:
            state = "approved" if charter_status == "approved" else "draft"
        return {
            "state": state,
            "charter_status": charter_status,
            "approved_on": _str(front.get("approved_on")),
            "approved_by": _str(front.get("approved_by")),
            "scope_sections": scope["sections"],
            "stakeholders": count_table_rows(self.texts.get(STAKEHOLDERS, "")),
            "lenses": count_bullets(self.texts.get(LENSES, ""), "Lenses"),
            "criteria": count_bullets(self.texts.get(LENSES, ""), "Evaluation criteria"),
        }


def _str(value) -> str:
    return value if isinstance(value, str) else ""


def _norm(text: str) -> str:
    return " ".join(text.split())


def scope_sections(lines: list, body: int) -> dict:
    """Each scope section as filled | empty | missing (seed guidance counts as empty)."""
    wanted = {"## Objectives": "Objectives", "### In scope": "In scope",
              "### Out of scope": "Out of scope", "## Deliverables": "Deliverables",
              "## Timeline": "Timeline", "## Constraints": "Constraints"}
    content: dict = {}
    current = None
    for line in lines[body:]:
        if line.startswith("#"):
            current = wanted.get(line.strip())
            if current is not None:
                content.setdefault(current, [])
            continue
        if current is not None:
            content[current].append(line)
    result = {}
    for section in SCOPE_SECTIONS:
        if section not in content:
            result[section] = "missing"
            continue
        text = _norm("\n".join(content[section]))
        seeds = {SEED_GUIDANCE_0_1.get(section), SEED_GUIDANCE_0_2.get(section)}
        result[section] = "empty" if not text or text in seeds else "filled"
    return result


def count_table_rows(text: str) -> int:
    rows = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            rows.append(line.strip())
        elif rows:
            break
    rows = [r for r in rows if not re.match(r"^\|[\s:|-]+\|?$", r)]
    return max(len(rows) - 1, 0)


def count_bullets(text: str, heading: str) -> int:
    count, inside = 0, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == heading
            continue
        if inside and re.match(r"^[-*] \S", line):
            count += 1
    return count


# --- Items, problems, gaps ---------------------------------------------------------


def item_view(entry: dict, type_: str) -> dict:
    f = entry["fields"]
    view = {
        "id": entry["id"], "type": type_, "title": entry["title"],
        "status": _str(f.get("status")), "origin": _str(f.get("origin")),
    }
    if type_ == "question":
        view["priority"] = _str(f.get("priority"))
        view["links"] = {"hypotheses": as_list(f.get("hypotheses"))}
    elif type_ == "hypothesis":
        question = f.get("question")
        view["links"] = {"question": question if isinstance(question, list) else _str(question)}
    else:
        view["links"] = {"questions": as_list(f.get("questions"))}
    view["supersedes"] = as_list(f.get("supersedes"))
    view["file"] = entry["file"]
    view["line"] = entry["line"]
    return view


def items(eng: Engagement) -> list:
    result = []
    for rel, (type_, _) in COLLECTIONS.items():
        for entry in eng.parsed.get(rel, {"entries": []})["entries"]:
            result.append(item_view(entry, type_))
    return result


def _holds_prefix(eng: Engagement, rel: str) -> str:
    holds = _str(eng.parsed[rel]["front"].get("holds"))
    return HOLDS_PREFIX.get(holds, COLLECTIONS[rel][1])


def find_problems(eng: Engagement) -> list:
    problems = []
    by_id: dict = {}
    typed = []  # (entry, type) for entries whose prefix matches their file
    for rel, (type_, _) in COLLECTIONS.items():
        if rel not in eng.parsed:
            continue
        parsed = eng.parsed[rel]
        problems += parsed["problems"]
        prefix = _holds_prefix(eng, rel)
        for e in parsed["entries"]:
            if e["id"] in by_id:
                first = by_id[e["id"]]
                problems.append(_problem("duplicate-id", e["id"], rel, e["line"],
                                         f"also at {first['file']}:{first['line']}"))
            else:
                by_id[e["id"]] = e
            ok = True
            if not e["well_formed"]:
                problems.append(_problem("malformed-id", e["id"], rel, e["line"],
                                         "heading must be `## <P>-<3+ digits>: <title>`"))
                ok = False
            elif e["id"][0] != prefix:
                problems.append(_problem("malformed-id", e["id"], rel, e["line"],
                                         f"this file holds {prefix}-IDs"))
                ok = False
            field_id = _str(e["fields"].get("id"))
            if ok and "id" in e["fields"] and field_id != e["id"]:
                problems.append(_problem("malformed-id", e["id"], rel, e["line"],
                                         f"heading ID differs from id field {field_id!r}"))
            if ok:
                typed.append((e, type_))

    ids = set(by_id)
    for e, type_ in typed:
        if e["parsed"]:  # an entry with unreadable lines is reported as unparseable only
            problems += entry_problems(e, type_, ids, by_id)

    superseded_by = set()
    for e, _ in typed:
        superseded_by.update(as_list(e["fields"].get("supersedes")))
    for e, _ in typed:
        f = e["fields"]
        status = _str(f.get("status"))
        if status == "superseded":
            if e["id"] not in superseded_by:
                problems.append(_problem("supersede-state", e["id"], e["file"], e["line"],
                                         "no item lists it in `supersedes`"))
            if not _str(f.get("change_reason")).strip():
                problems.append(_problem("supersede-state", e["id"], e["file"], e["line"],
                                         "`change_reason` is empty"))
        if status == "rejected" and not _str(f.get("change_reason")).strip():
            problems.append(_problem("reject-state", e["id"], e["file"], e["line"],
                                     "`change_reason` is empty"))

    problems += scope_problems(eng)
    problems.sort(key=lambda p: (p["file"] or "", p["line"] or 0, p["code"]))
    return problems


def entry_problems(e: dict, type_: str, ids: set, by_id: dict) -> list:
    f, rel, line, id_ = e["fields"], e["file"], e["line"], e["id"]
    out = []
    missing = [k for k in STANDARD_FIELDS + TYPE_FIELDS[type_] if k not in f]
    if missing:
        out.append(_problem("missing-field", id_, rel, line, "missing: " + ", ".join(missing)))
    for key, allowed in ALLOWED.items():
        if key in f and f[key] not in allowed:
            out.append(_problem("bad-value", id_, rel, line, f"{key}: {f[key]!r}"))
    if type_ == "question" and _str(f.get("priority")) and f["priority"] not in PRIORITIES:
        out.append(_problem("bad-value", id_, rel, line, f"priority: {f['priority']!r}"))
    trigger = f.get("change_trigger", "")
    if trigger and trigger not in TRIGGERS:
        out.append(_problem("bad-value", id_, rel, line, f"change_trigger: {trigger!r}"))
    if "confidence_reason" in f and not _str(f["confidence_reason"]).strip():
        out.append(_problem("bad-value", id_, rel, line, "confidence_reason is empty"))
    if f.get("audience") == "client-ready":
        out.append(_problem("client-ready", id_, rel, line, "charter items stay internal"))
    if f.get("origin") == "client-document":
        out.append(_problem("cited-source", id_, rel, line, "origin is client-document"))
    for key, value in f.items():
        values = value if isinstance(value, list) else [value]
        if any(isinstance(v, str) and SOURCE_ID.search(v) for v in values):
            out.append(_problem("cited-source", id_, rel, line, f"source ID in `{key}`"))

    for key in LINK_FIELDS:
        for target in as_list(f.get(key)):
            if QHA_TOKEN.match(target) and target not in ids:
                out.append(_problem("broken-link", id_, rel, line, f"{key}: {target} does not exist"))

    if type_ == "hypothesis":
        q = f.get("question")
        qs = as_list(q)
        if len(qs) != 1 or not re.match(r"^Q-\d{3,}$", qs[0]) or qs[0] not in by_id:
            out.append(_problem("hypothesis-question", id_, rel, line,
                                "`question` must be exactly one existing Q-ID"))
        else:
            target = by_id[qs[0]]
            if target["parsed"] and id_ not in as_list(target["fields"].get("hypotheses")):
                out.append(_problem("one-way-link", id_, rel, line,
                                    f"question {qs[0]} does not list {id_}"))
    if type_ == "question":
        for h in as_list(f.get("hypotheses")):
            if h in by_id and h.startswith("H-") and by_id[h]["parsed"]:
                back = as_list(by_id[h]["fields"].get("question"))
                if back != [id_]:
                    other = back[0] if back else "no question"
                    out.append(_problem("one-way-link", id_, rel, line,
                                        f"{h} links to {other}, not {id_}"))
    return out


def scope_problems(eng: Engagement) -> list:
    out = []
    scope_front = eng.scope()["front"]
    record = eng.record
    if SCOPE in eng.texts:
        for key in ("model_use", "model_use_notes"):
            if _str(scope_front.get(key)) != _str(record.get(key)):
                out.append(_problem("model-use-mismatch", None, SCOPE, None,
                                    f"`{key}` differs from engagement.md"))
    if _str(scope_front.get("charter_status")) == "approved" and _str(record.get("model_use")) == "unconfirmed":
        out.append(_problem("approved-unconfirmed", None, SCOPE, None,
                            "the charter is approved while model_use is unconfirmed"))
    if eng.uses_code_name and eng._client:
        needle = eng._client.lower()
        for rel in sorted(eng.texts):
            if (rel.startswith("00-charter/") and "/" not in rel[len("00-charter/"):]) or rel == CHANGELOG:
                if needle in eng.texts[rel].lower():
                    out.append(_problem("real-name-leak", None, rel, None,
                                        "the real client name appears in this file; use the code name"))
    return out


def find_gaps(eng: Engagement, charter: dict) -> list:
    gaps = []
    live = [(e, t) for e, t in _typed_entries(eng) if e["fields"].get("status") in LIVE]
    questions = [e for e, t in live if t == "question"]
    hypotheses = [e for e, t in live if t == "hypothesis"]
    answered = {q for h in hypotheses for q in as_list(h["fields"].get("question"))}
    for q in questions:
        if q["id"] not in answered:
            gaps.append({"code": "question-no-hypothesis", "id": q["id"]})
    for h in hypotheses:
        if not _str(h["fields"].get("reject_if")).strip():
            gaps.append({"code": "hypothesis-no-reject", "id": h["id"]})
        if not _str(h["fields"].get("confirm_if")).strip():
            gaps.append({"code": "hypothesis-no-confirm", "id": h["id"]})
    for a, t in live:
        if t == "assumption" and not _str(a["fields"].get("basis")).strip():
            gaps.append({"code": "assumption-no-basis", "id": a["id"]})
    for section, state in charter["scope_sections"].items():
        if state != "filled":
            gaps.append({"code": "scope-section-empty", "section": section})
    if charter["stakeholders"] == 0:
        gaps.append({"code": "no-stakeholders"})
    if charter["lenses"] == 0:
        gaps.append({"code": "no-lenses"})
    no_priority = sum(1 for q in questions if not _str(q["fields"].get("priority")).strip())
    if len(questions) > 10 and no_priority * 2 > len(questions):
        gaps.append({"code": "many-questions"})
    return gaps


def _typed_entries(eng: Engagement) -> list:
    result = []
    for rel, (type_, prefix) in COLLECTIONS.items():
        for e in eng.parsed.get(rel, {"entries": []})["entries"]:
            if e["well_formed"] and e["id"][0] == prefix:
                result.append((e, type_))
    return result


def pending_revisions(eng: Engagement) -> list:
    status = {e["id"]: e["fields"].get("status") for e, _ in _typed_entries(eng)}
    result = []
    for e, _ in _typed_entries(eng):
        if e["fields"].get("status") != "proposed":
            continue
        for old in as_list(e["fields"].get("supersedes")):
            if status.get(old) != "superseded":
                result.append({"new": e["id"], "old": old})
    return result


# --- Commands ---------------------------------------------------------------------


def cmd_status(eng: Engagement, args) -> tuple:
    charter = eng.charter_block()
    proposed = sum(1 for e, _ in _typed_entries(eng) if e["fields"].get("status") == "proposed")
    return EXIT_OK, {
        "engagement": eng.engagement_block(),
        "charter": charter,
        "items": items(eng),
        "pending_revisions": pending_revisions(eng),
        "proposed_since_approval": proposed if charter["charter_status"] == "approved" else 0,
        "next_ids": eng.next_ids(),
        "problems": find_problems(eng),
        "gaps": find_gaps(eng, charter),
    }


def cmd_check(eng: Engagement, args) -> tuple:
    problems = find_problems(eng)
    checked = {"Q": 0, "H": 0, "A": 0}
    for e in eng.entries():
        if e["id"][:1] in checked:
            checked[e["id"][0]] += 1
    return (EXIT_PROBLEMS if problems else EXIT_OK), {
        "ok": not problems, "problems": problems, "checked": checked,
    }


def cmd_refs(eng: Engagement, args) -> tuple:
    for id_ in args.ids:
        if not ID_TOKEN.match(id_):
            raise Fail(EXIT_USAGE, f"not an object ID: {id_!r} (expected for example Q-002)")
    wanted = {id_: re.compile(rf"\b{re.escape(id_)}\b") for id_ in args.ids}
    refs: dict = {id_: [] for id_ in args.ids}
    for rel in sorted(eng.texts):
        if rel == CHANGELOG:
            continue
        parsed = eng.parsed.get(rel) or parse_file(eng.texts[rel], rel)
        objects = []
        own_id = _str(parsed["front"].get("id"))
        if own_id:
            objects.append((own_id, parsed["front"]))
        objects += [(e["id"], e["fields"]) for e in parsed["entries"]]
        for obj_id, fields in objects:
            for key, value in fields.items():
                if key == "id":
                    continue
                values = value if isinstance(value, list) else [value]
                for id_, pattern in wanted.items():
                    if any(isinstance(v, str) and pattern.search(v) for v in values):
                        refs[id_].append({"id": obj_id, "field": key, "file": rel})
    return EXIT_OK, {"refs": refs}


def cmd_model_use(eng: Engagement, args) -> tuple:
    value = args.set
    notes = " ".join((args.notes or "").split())
    paths = {"engagement.md": eng.root / "engagement.md", SCOPE: eng.root / SCOPE,
             CHANGELOG: eng.root / CHANGELOG}
    originals = {}
    for rel, path in paths.items():
        text = None
        try:
            text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            pass
        if text is None:
            raise Fail(EXIT_USAGE, f"could not read {rel}; nothing was written")
        originals[rel] = text

    old_value = _str(eng.record.get("model_use"))
    new = {
        "engagement.md": set_policy_front_matter(originals["engagement.md"], value, notes, "engagement.md"),
        SCOPE: set_policy_scope(originals[SCOPE], value, notes),
    }
    changed = [rel for rel in ("engagement.md", SCOPE) if new[rel] != originals[rel]]
    if not changed:
        return EXIT_OK, {"model_use": value, "model_use_notes": notes, "changed": []}

    reason = f"{old_value or '(none)'} → {value}" + (f" ({notes})" if notes else "")
    reason = reason.replace(" · ", " - ")
    line = f"{date.today().isoformat()} · model-use · model-use · {reason} · -"
    new[CHANGELOG] = append_changelog(originals[CHANGELOG], line)
    for rel in changed + [CHANGELOG]:
        atomic_write(paths[rel], new[rel])
    return EXIT_OK, {"model_use": value, "model_use_notes": notes, "changed": changed + [CHANGELOG]}


def _split_comment(rest: str) -> tuple:
    """Split the text after `key:` into (value, trailing comment with its spacing)."""
    s = rest.lstrip()
    if s[:1] in ("'", '"'):
        end = _find_close_quote(s, s[0])
        if end >= 0:
            after = s[end + 1 :]
            return s[: end + 1], after if after.strip().startswith("#") else ""
    match = re.search(r"\s+#", s)
    if match:
        return s[: match.start()], s[match.start() :]
    return s, ""


def set_policy_front_matter(text: str, value: str, notes: str, rel: str) -> str:
    lines = text.split("\n")
    fm_lines, body = split_front_matter(lines)
    if fm_lines is None:
        raise Fail(EXIT_USAGE, f"{rel} has no front matter; nothing was written")
    end = body - 1  # index of the closing ---
    use_at = next((i for i in range(1, end) if lines[i].startswith("model_use:")), None)
    if use_at is None:
        raise Fail(EXIT_USAGE, f"no `model_use:` line in {rel}; nothing was written")
    _, comment = _split_comment(lines[use_at][len("model_use:"):])
    lines[use_at] = f"model_use: {value}{comment}"
    notes_line = "model_use_notes: " + json.dumps(notes, ensure_ascii=False)
    notes_at = next((i for i in range(1, end) if lines[i].startswith("model_use_notes:")), None)
    if notes_at is None:
        lines.insert(use_at + 1, notes_line)
    else:
        _, comment = _split_comment(lines[notes_at][len("model_use_notes:"):])
        lines[notes_at] = notes_line + comment
    return "\n".join(lines)


POLICY_PREFIX = re.compile(r"^Current policy: \*\*[^*]*\*\*\.?")


def set_policy_scope(text: str, value: str, notes: str) -> str:
    text = set_policy_front_matter(text, value, notes, SCOPE)
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.strip() == "## Model use"), None)
    if start is None:
        raise Fail(EXIT_USAGE, f"no `## Model use` section in {SCOPE}; nothing was written")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    policy_at = next((i for i in range(start + 1, end) if lines[i].startswith("Current policy:")), None)
    if policy_at is None:
        raise Fail(EXIT_USAGE, f"no `Current policy:` line in {SCOPE}; nothing was written")
    match = POLICY_PREFIX.match(lines[policy_at])
    if not match:
        raise Fail(EXIT_USAGE, f"the `Current policy:` line in {SCOPE} is not in the expected form")
    shown = notes if notes else "none recorded"
    if not shown.endswith((".", "!", "?")):
        shown += "."
    restrictions = f"Restrictions: {shown}"
    rest = lines[policy_at][match.end():].strip()
    lines[policy_at] = f"Current policy: **{value}**." + (f" {rest}" if rest else "")
    restr_at = next((i for i in range(start + 1, end) if lines[i].startswith("Restrictions:")), None)
    if restr_at is not None:
        lines[restr_at] = restrictions
    elif rest:
        # 0.1.0 shape: the explanation continues on the policy line. Give it its own paragraph.
        lines[policy_at] = f"Current policy: **{value}**."
        lines[policy_at + 1 : policy_at + 1] = [restrictions, "", rest]
    else:
        lines.insert(policy_at + 1, restrictions)
    return "\n".join(lines)


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


# --- Entry point ------------------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="charter.py", description="Helper for the Cairn `charter` skill.")
    parser.add_argument("--root", help="engagement folder (skips discovery)")
    parser.add_argument("--version", action="version", version=f"charter.py {SCRIPT_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="engagement facts, items, next IDs, problems and gaps")
    sub.add_parser("check", help="problems only; exit 1 when there are any")
    refs = sub.add_parser("refs", help="objects whose fields link to the given IDs")
    refs.add_argument("ids", nargs="+", metavar="ID")
    model = sub.add_parser("model-use", help="set the model-use policy in both files")
    model.add_argument("--set", required=True, choices=MODEL_USE_VALUES)
    model.add_argument("--notes", default="")
    return parser


COMMANDS = {"status": cmd_status, "check": cmd_check, "refs": cmd_refs, "model-use": cmd_model_use}


def main(argv=None, script_path=__file__) -> int:
    args = build_parser().parse_args(argv)
    try:
        eng = Engagement(find_root(args.root, script_path=script_path))
        code, result = COMMANDS[args.command](eng, args)
    except Fail as exc:
        sys.stderr.write(exc.message + "\n")
        return exc.code
    out = json.dumps(eng.redact(result), ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(out.encode("utf-8"))
    sys.stdout.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
