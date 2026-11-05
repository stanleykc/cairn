# Contract: `ingest.py` helper script

`<engagement>/.claude/skills/ingest/scripts/ingest.py`. Python 3.9+, standard library
only, no network access (research R3). It reads and writes plain files only. For PDFs, it
calls the local poppler tools `pdftotext`, `pdfinfo` and `pdfimages` when they're on
`PATH` (checked mode). Without them it works in unchecked mode (R4).

~~~text
python3 ingest.py [--root PATH] status [RAW ...]
python3 ingest.py [--root PATH] extract RAW [--as {document,transcript}] [--sendable] [--restart]
python3 ingest.py [--root PATH] register-restricted RAW
python3 ingest.py [--root PATH] verify [ID ...]
python3 ingest.py [--root PATH] finalize ID
python3 ingest.py [--root PATH] review ID [ID ...]
python3 ingest.py [--root PATH] set-status ID {active,rejected} [--reason TEXT] [--trigger {new-evidence,client-feedback,rethinking}]
python3 ingest.py [--root PATH] restrict ID --reason TEXT [--remove-content --by NAME]
python3 ingest.py [--root PATH] refs ID [ID ...]
python3 ingest.py --version
~~~

`RAW` is a path relative to `10-sources/raw/` (an absolute path or one relative to the
engagement root is accepted if it resolves inside `raw/`). `--root` and engagement
discovery work as in `charter.py` (002 R5). The not-in-engagement message names `ingest`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. For `verify`, no problems (warnings may be present). |
| 1 | `verify` or `finalize` found problems. The JSON is still printed. `finalize` writes nothing. |
| 2 | Not inside an engagement, or the engagement record is unreadable. |
| 3 | **Policy refusal**: `extract` under `unconfirmed`, or under `restricted` without `--sendable`. Nothing is opened or written. |
| 4 | **Duplicate**: `extract` found an identical original. The JSON names `duplicate_of`. Nothing is written. |
| 5 | **Can't extract**: unsupported format, unreadable file (encrypted, damaged, empty, unknown encoding, or a PDF without a `%PDF-` header), `transcript-format-unknown`, or a `RAW` outside `raw/`. The JSON has `reason`. Nothing is written. |
| 6 | Bad arguments, an unknown ID, or a state that doesn't allow the command (for example `finalize` on a complete source, or `set-status` on an in-progress one). Nothing is written. |

## Files read and written

| Command | Opens files in `raw/`? | Writes |
|---|---|---|
| `status` | No. Lists names and sizes only. | nothing |
| `extract` | Yes, the one named file, after the policy gate | `10-sources/extracted/S-###.md` (in-progress), `.cairn/work/ingest/S-###/` (Word images) |
| `register-restricted` | **Never** | `10-sources/extracted/S-###.md` (complete, restricted), index row |
| `verify` | Yes, the originals of the named (or all unrestricted, complete or in-progress) sources, to compare | nothing |
| `finalize` | Yes, as `verify` | the source's front matter (`extraction_status`), index row, deletes `.cairn/work/ingest/S-###/` |
| `review`, `refs` | No | nothing |
| `set-status` | No | the source (and the superseded source), index rows, changelog |
| `restrict` | No | the source, index row, changelog |

Always:
- Nothing under `10-sources/raw/` is ever written, renamed, moved or deleted. Files are
  opened read-only (`"rb"`).
- A `restricted: true` source's original is never opened by any command.
- No command opens anything in `raw/` while the policy is `unconfirmed`.
- Every write is atomic (temp file + `os.replace`).
- Stdout never contains extracted text, only IDs, locators, labels, counts, paths and
  codes. Speaker labels are the one exception: they come from the content and are needed
  to ask the consultant who the speakers are.

## Output

JSON on stdout, UTF-8, one object. Keys are stable within a framework minor version.

### `status`

~~~json
{
  "engagement": {"root": "/abs", "id": "…", "engagement_name": "…", "client_label": "Northwind",
                 "uses_code_name": true, "lead_consultant": "Test Lead",
                 "framework_version": "0.3.0", "model_use": "restricted",
                 "model_use_notes": "No HR files or interview transcripts"},
  "pdf_backend": {"available": true, "mode": "checked | unchecked",
                  "tools": ["pdftotext", "pdfinfo", "pdfimages"],
                  "install_hint": "brew install poppler  |  apt install poppler-utils"},
  "raw_files": [
    {"raw": "ops/ops-review-fy25.pdf", "format": "pdf", "bytes": 482113,
     "state": "new", "source_id": null},
    {"raw": "kickoff.vtt", "format": "vtt", "bytes": 20411, "state": "ingested", "source_id": "S-002"},
    {"raw": "slides.pptx", "format": "pptx", "bytes": 1203321, "state": "unsupported", "source_id": null}
  ],
  "sources": [
    {"id": "S-001", "title": "…", "material": "document", "status": "proposed",
     "extraction_status": "complete", "restricted": false, "raw_file": "…",
     "original_present": true, "derived": true, "uncertain": 2, "supersedes": []}
  ],
  "next_id": "S-003",
  "work_folders": [],
  "problems": []
}
~~~

`status RAW ...` limits `raw_files` to the named files. A named file outside `raw/` is
reported with `state: "outside-raw"`, and the skill offers to copy it in.

### `extract`

~~~json
{
  "id": "S-003", "file": "10-sources/extracted/S-003.md", "resumed": false,
  "raw": "ops/ops-review-fy25.pdf", "format": "pdf", "material_guess": "document",
  "origin_guess": "client-document",
  "pdf": {"page_count": 42, "pages_reviewed": 0,
          "pages": [{"page": 1, "chars": 1830, "label": "i", "images": 0},
                    {"page": 7, "chars": 0, "label": "5", "images": 1}],
          "low_text_pages": [7, 19], "image_pages": [7, 12, 19], "label_differs": [1, 2]},
  "docx": null,
  "transcript": null,
  "uncertain": ["p. 7 — no text layer"],
  "next": "view pages 1–20 with Read, then edit the file; run verify"
}
~~~

In unchecked mode (no poppler), `pdf` is
`{"mode": "unchecked", "page_count_estimate": 42, "pages_reviewed": 0}`. The content region
is empty, and `next` tells the assistant to copy each page's text under `### p. n`
markers, set `page_count` from Read, and add the same callouts as in checked mode. The
source has `fidelity: unchecked`.

For Word, `docx` is
`{"headings": n, "tables": n, "images": [{"locator": "§ A > B", "path": ".cairn/work/ingest/S-003/image2.png", "viewable": true}], "charts": n, "comments": n, "tracked_changes": n, "footnotes": n}`.

For transcripts, `transcript` is
`{"shape": "vtt-voice|vtt-prefix|srt-prefix|name-colon|bold-name|bracket-time|name-time-line|name-paren-time|unlabelled", "turns": n, "timestamps": true, "labels": ["Speaker 1", "Dana"], "generic_labels": ["Speaker 1"]}`.

Policy refusal (exit 3):

~~~json
{"refused": "policy-unconfirmed", "detail": "Settle model use with charter first. No file was opened."}
~~~

### `register-restricted`

Writes the record with `restricted: true`, `extraction_method: none`, `raw_sha256: ""`,
`extraction_status: complete`, `status: proposed` and `audience: internal`, then adds the
index row. Returns `{"id": "S-004", "file": "…"}`. The assistant then fills in the
consultant's details (title, material, date, provider) and runs `verify`.

### `verify`

~~~json
{"problems": [{"code": "content-mismatch", "id": "S-003", "locator": "p. 12", "line": 233,
               "detail": "3 words differ from the text layer"}],
 "warnings": [{"code": "original-missing", "id": "S-001", "detail": "raw/old-name.pdf not found"}]}
~~~

Codes: [data-model §8](../data-model.md#8-validation-rules-verify-problem-codes). Without
IDs, `verify` checks every source and the index.

### `finalize`

Runs `verify` on the source. If it passes, sets `extraction_status: complete`, sets
`fidelity: checked` when the word-for-word comparison ran (an unchecked source stays
`unchecked`), adds the index row and deletes the work folder. Returns `{"id": "S-003", "index_row": "| S-003 | … |"}`.

### `review`

~~~json
{"sources": [{"id": "S-003", "title": "…", "status": "proposed",
  "derived": [{"locator": "p. 7", "kind": "ocr", "line": 140}],
  "tables": [{"locator": "p. 12", "rows": 9, "cols": 4, "line": 230, "built_by": "assistant"}],
  "uncertain": [{"locator": "p. 19", "line": 40}],
  "corrected": [], "comments": 0, "tracked_changes": 0,
  "fidelity": "unchecked", "sample_pages": [2, 9, 17]}]}
~~~

`sample_pages` appears only for unchecked sources: up to three text pages, spread across
the document, for the consultant to compare against the page image. Unchecked sources
come first in the output.

Line numbers let the assistant show each passage with `Read` (offset and limit) without
reading the whole file.

### `set-status`

`rejected` is also allowed on an in-progress source (for example, a PDF that Read can't
open). No index row is written for it.

`active`: allowed only on a complete source. If it `supersedes` S-old, S-old becomes
`superseded` (with `change_reason` and `change_trigger` copied over), and a `supersede`
line is logged. `rejected`: needs `--reason` and `--trigger`, sets `change_reason` and
`change_trigger`, and logs `reject`. The index rows are updated. Returns
`{"changed": [{"id": "S-007", "status": "active"}, {"id": "S-002", "status": "superseded"}], "log": ["…"], "refs": [...]}`.
`refs` lists objects citing any superseded or rejected source (same shape as `refs`).

### `restrict`

Sets `restricted: true` and logs `restrict`. With `--remove-content`, it also replaces the
content region with the restricted notice, clears the `## Speakers` names and
`## Uncertain passages`, sets `content_removed: true`, and logs `remove-content` naming
`--by`. The index row is updated. Returns `{"id": …, "removed": bool, "refs": [...]}`.

### `refs`

~~~json
{"refs": {"S-003": [{"id": "O-014", "field": "source", "file": "30-observations/O-014.md"}]}}
~~~

Scans every Cairn object outside `10-sources/` and `_templates/`, in the fields `source`,
`derived_from`, `supports`, `contradicts`, `supersedes` and `clarifies`. It outputs IDs
and paths only.
