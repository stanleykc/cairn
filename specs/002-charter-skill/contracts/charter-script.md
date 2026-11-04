# Contract: `charter.py` helper script

`<engagement>/.claude/skills/charter/scripts/charter.py`. Python 3.9+, standard library
only, no network access (research R3). It reads and writes plain files only.

~~~text
python3 charter.py [--root PATH] status
python3 charter.py [--root PATH] check
python3 charter.py [--root PATH] refs ID [ID ...]
python3 charter.py [--root PATH] model-use --set {allowed,restricted,unconfirmed} [--notes TEXT]
python3 charter.py --version
~~~

`--root` skips engagement discovery (used by tests). Without it, the script walks up from
the current directory, then tries the script's own engagement (R5).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. For `check`, no problems found. |
| 1 | `check` found problems. The JSON is still printed. |
| 2 | Not inside an engagement, or the engagement record is unreadable. The message goes to stderr. |
| 3 | Bad arguments (argparse), or `model-use` couldn't find a line or section to rewrite. Nothing is written. |

## Files read and written

| Command | Reads | Writes |
|---|---|---|
| `status`, `check` | `engagement.md`, `00-charter/*.md`, `60-log/changelog.md`; for ID numbering, every `*.md` under the content folders except `10-sources/` and `_templates/` | nothing |
| `refs` | same set as above | nothing |
| `model-use` | `engagement.md`, `00-charter/scope.md` | the same two files, each rewritten atomically (temp file + `os.replace`). Only the `model_use` and `model_use_notes` lines, and the Model use section lines `Current policy:` and `Restrictions:`, are changed. The script then appends one `model-use` event to the changelog. |

Never read: anything under `10-sources/`. Never written: anything outside the files in the
table.

## Output

JSON on stdout, UTF-8, one object. Keys are stable. New keys may be added, and existing
keys aren't removed or renamed within a framework minor version.

### `status`

~~~json
{
  "engagement": {
    "root": "/abs/path",
    "id": "acme-fulfillment-review",
    "engagement_name": "Fulfillment Review",
    "client_label": "Acme",
    "uses_code_name": false,
    "lead_consultant": "Test Lead",
    "framework_version": "0.2.0",
    "model_use": "unconfirmed",
    "model_use_notes": ""
  },
  "charter": {
    "state": "empty | draft | approved",
    "charter_status": "draft",
    "approved_on": "",
    "approved_by": "",
    "scope_sections": {"Objectives": "filled|empty|missing", "In scope": "…", "Out of scope": "…",
                       "Deliverables": "…", "Timeline": "…", "Constraints": "…"},
    "stakeholders": 0,
    "lenses": 0,
    "criteria": 0
  },
  "items": [
    {"id": "Q-001", "type": "question", "title": "…", "status": "proposed",
     "origin": "consultant-note", "priority": "high",
     "links": {"hypotheses": ["H-001"]}, "supersedes": [], "file": "00-charter/questions.md", "line": 14}
  ],
  "pending_revisions": [{"new": "H-004", "old": "H-002"}],
  "proposed_since_approval": 0,
  "next_ids": {"Q": "Q-001", "H": "H-001", "A": "A-001"},
  "problems": [{"code": "one-way-link", "id": "H-002", "file": "00-charter/hypotheses.md",
                "line": 30, "detail": "question Q-001 does not list H-002"}],
  "gaps": [{"code": "question-no-hypothesis", "id": "Q-002"}]
}
~~~

- `items[].title` is included for charter items only. Text from objects outside
  `00-charter/` is never output (R6).
- When `uses_code_name` is true, the real client name appears nowhere in the output (R7).
- Problem and gap codes are listed in [data-model.md](../data-model.md) §5.2 and §5.4.

### `check`

~~~json
{"ok": false, "problems": [ … same shape as status.problems … ], "checked": {"Q": 4, "H": 3, "A": 2}}
~~~

### `refs ID …`

~~~json
{"refs": {"Q-002": [{"id": "O-014", "field": "questions", "file": "30-observations/O-014.md"},
                    {"id": "H-003", "field": "question", "file": "00-charter/hypotheses.md"}]}}
~~~

An ID with no references maps to `[]`. Each object's own `id` field and the changelog are
excluded.

### `model-use`

~~~json
{"model_use": "restricted", "model_use_notes": "No transcripts to external AI; decks OK.",
 "changed": ["engagement.md", "00-charter/scope.md", "60-log/changelog.md"]}
~~~

If the value and the notes are already as given, nothing is written and `changed` is
`[]`. A missing `model_use_notes:` line in either file is added directly after
`model_use:`, and a missing `Restrictions:` line is added after `Current policy:`.
Comments after the value (`# allowed | restricted | unconfirmed`) are kept.
