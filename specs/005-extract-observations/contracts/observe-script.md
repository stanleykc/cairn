# Contract: `observe.py` helper script

`skills/extract-observations/scripts/observe.py`. Standard library, Python 3.9+ (R3).
Run from anywhere inside the engagement:

```text
python3 <skill base directory>/scripts/observe.py <command> [args]
```

Every command prints **one JSON object** to stdout and nothing else. It never prints source
text beyond the passages and claims of existing observations (which are already
engagement records). Field and check rules: [data-model](../data-model.md).

## Exit codes

| Code | Meaning | Written? |
|---|---|---|
| 0 | success (for `add`: at least the request was processed; see `refused`) | as reported |
| 1 | `verify` found problems | nothing |
| 2 | not inside an engagement | nothing |
| 3 | policy refusal: `unconfirmed`, or a restricted / content-removed source (for `add`: in any draft) | nothing |
| 6 | bad arguments or wrong state (unknown or in-progress source, retired source without `--confirmed`, unreadable drafts file) | nothing |

## Commands

### `status [S-ID …]`

Engagement facts and the work list. Reads `engagement.md`, source front matter, questions
and observations; opens no source content.

```json
{
  "engagement_name": "Fulfilment review",
  "client_label": "Northwind",
  "uses_code_name": true,
  "model_use": "allowed",
  "questions": [{"id": "Q-003", "title": "Why is fulfilment slow?", "status": "active"}],
  "next_id": "O-015",
  "sources": [
    {"id": "S-004", "title": "…", "material": "document", "status": "active",
     "extraction_status": "complete", "restricted": false, "content_removed": false,
     "observations": 12, "progress": {"state": "stopped", "stopped_at": "p. 18"},
     "eligible": true, "reason": ""}
  ]
}
```

- `eligible: false` with `reason` one of `restricted`, `content-removed`, `in-progress`,
  `retired` (rejected/superseded; `superseded_by` given), `llm-inference`.
- With no IDs: every source. Under `unconfirmed`: exit 3 with
  `{"error": "policy-unconfirmed", "message": "…settle model use with /charter…"}`.

### `prepare S-ID [--confirmed]`

Gate and outline for one source. Run it before reading the source file.

```json
{
  "source": {"id": "S-004", "material": "meeting-transcript", "origin": "interview-meeting",
             "confidence": "medium", "author_kind": "", "status": "proposed",
             "source_not_approved": true, "fidelity": "checked",
             "uncertain_passages": ["00:31:10"], "path": "10-sources/extracted/S-004.md",
             "content_lines": [41, 812]},
  "cap": "medium",
  "units": [{"locator": "T1", "timestamp": "00:00:04", "speaker": "Dana Reyes", "line": 42}],
  "tables": [{"unit": "p. 2", "table": 1, "rows": 2, "columns": ["Site", "Orders", "Avg days to ship"], "line": 60}],
  "derived": [{"unit": "p. 2", "kind": "vision-description", "line": 66}],
  "speakers": [{"label": "Speaker 1", "name": "Dana Reyes"}],
  "existing": [{"id": "O-009", "status": "rejected", "locator": "T12", "questions": [],
                "claim": "…", "passage": "…", "folder": "_inbox"}],
  "progress": {"state": "stopped", "stopped_at": "T120", "steering": {…}},
  "superseded_by": ""
}
```

Exit 3 / 6 per the gates (R13). `--confirmed` is required for a `rejected` or `superseded`
source.

### `add DRAFTS.json [--dry-run] [--confirmed]`

Checks each draft and writes the accepted ones as `_inbox/O-###.md`, in draft order, one
atomic file write each.

```json
{
  "written": [{"id": "O-015", "title": "…", "source": "S-004", "locator": "T17",
               "questions": ["Q-003"], "derived": false, "confidence": "medium"}],
  "refused": [{"index": 3, "code": "quote-not-found", "detail": "…"}],
  "warnings": [{"index": 5, "code": "same-passage", "existing": "O-011", "detail": "…"}],
  "next_id": "O-017"
}
```

- A draft with a refusal code, or with a warning not in its `accept_warnings`, is not
  written. Warnings in `accept_warnings` are written and echoed.
- `--dry-run` runs every check and writes nothing.
- Gates are re-checked for every draft's source (R13), **before any file is written**. If
  any draft's source fails a policy gate (`model_use: unconfirmed`, or a restricted /
  content-removed source), the whole run stops with exit 3 and **nothing is written**, not
  even the drafts for other sources. The JSON names the code and the source. Every other
  gate (unknown, in-progress, `llm-inference`, retired without `--confirmed`) refuses only
  that draft and goes in `refused`.
- `--confirmed` lets drafts cite a `rejected` or `superseded` source, after the consultant
  confirmed it (as for `prepare`).

### `progress S-ID (--stopped-at LOCATOR | --done) [--steering-from DRAFTS.json]`

Updates `.cairn/work/extract-observations/progress.json` (data-model §4).

### `tag O-ID Q-ID [Q-ID …]`

Adds the question IDs to `questions` (skipping any already present), changes nothing else,
and appends `YYYY-MM-DD · O-ID · tag · added Q-… · -` to `60-log/changelog.md`. Refuses
unknown observation or question IDs (exit 6). Run only after the consultant confirms.

### `verify [O-ID …]`

Re-checks stored observations (all when no IDs): fields, quote at locator, caps, links,
status values, leak. Exit 1 with `{"problems": [...]}` when any are found.

## File access

| Path | Access |
|---|---|
| `engagement.md` | read |
| `00-charter/questions.md` | read |
| `10-sources/extracted/S-###.md` | read (front matter always; content only for eligible sources) |
| `10-sources/raw/` | **never** opened |
| `_inbox/`, `30-observations/` | read; `add` creates new files in `_inbox/`; `tag` edits the `questions` line |
| `60-log/changelog.md` | `tag` appends |
| `.cairn/work/extract-observations/` | read and write |
| anything else | read only for ID scanning (R8) |

No network access, no subprocesses.
