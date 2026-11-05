# Data Model: Ingest Skill

This feature writes the first sources in an engagement. It uses the containers and
templates from feature 001 ([001 data model](../001-engagement-init/data-model.md)) and the
change convention from feature 002
([change-convention.md](../002-charter-skill/contracts/change-convention.md)), with the
changes in §1. Every rule here is checked by `ingest.py verify`
([contracts/ingest-script.md](contracts/ingest-script.md)), unless it is marked
*(assistant)*.

## 1. Changes to the framework data model

| Change | Files | Why |
|---|---|---|
| Source template: new fields `material`, `raw_sha256`, `raw_bytes`, `meeting_title`, `meeting_date`, `attendees`, `author`, `author_kind`, `extraction_status`, `fidelity`, `page_count`, `pages_reviewed`, `content_removed`. `source_type` values become file formats. `extraction_method` gains `none`. New body sections (§3.3). | `assets/templates/source.md` | FR-018, FR-023, the resume, duplicate and restricted edge cases (R8) |
| Change convention: new events `extraction-fix`, `restrict` and `remove-content`. Subject form `<ID> @ <locator>`. Trigger `-` allowed for those three events. | `assets/skills/charter/reference/change-convention.md`, new identical copy in `assets/skills/ingest/reference/`, `specs/002-charter-skill/contracts/change-convention.md`, `assets/seed/60-log/changelog.md` guidance | FR-031, restriction after ingest (R14) |
| Framework version `0.2.0` → `0.3.0` | `src/cairn/__init__.py` | Refresh delivers the skill and the template (R20) |
| 001 docs updated for the source fields | `specs/001-engagement-init/data-model.md` (source row) | The constitution requires the data model docs to move with the templates |

The source index (`10-sources/index.md`) keeps its columns. No folder is added. The work
folder `.cairn/work/ingest/` is temporary and sits inside `.cairn/`, the existing internal
folder (R13).

## 2. Original

A file as received, in `10-sources/raw/` or a subfolder of it.

| Attribute | Derived from | Notes |
|---|---|---|
| path | relative to `10-sources/raw/` | Stored in the source's `raw_file` |
| format | file extension, case-insensitive | `.pdf` `.docx` `.md` `.markdown` `.txt` `.vtt` `.srt` are supported. Anything else is `unsupported` (FR-004). |
| hash | SHA-256 of the bytes | Taken only by `extract`, so a restricted file is never hashed (R6) |
| size | bytes, from `stat` | Read without opening the file. Recorded as `raw_bytes` for every source, including restricted records. |
| state (derived by `status`) | matching `raw_file` of existing sources | `new` · `in-progress` (S-ID) · `ingested` (S-ID) · `restricted` (S-ID) · `rejected` (S-ID, rejected while in progress) · `unsupported` |
| `possible_restricted_copy` (derived by `status`) | a `new` file whose size equals a restricted source's `raw_bytes`, or whose name stem equals one once version suffixes are stripped (R15) | The restricted S-ID, or `null` |

**Invariant**: No command writes, renames, moves or deletes anything under `raw/` (FR-026).
The only write the skill makes there is a copy into `raw/`, made at the consultant's
request with the assistant's file tools *(assistant)*.

Duplicates by content (FR-027) are found by `extract`, which compares the hash with every
source's `raw_sha256` before writing.

A restricted record has no hash, so a copy of a restricted file can't be found by content.
Instead, `status` flags a new file as `possible_restricted_copy` by size or name, and
`extract` treats it as restricted: it requires `--sendable` under **every** policy, which the
skill passes only after the consultant confirms that the file may be sent (R6).

A file whose source was rejected while in progress (for example an unreadable PDF) has state
`rejected`. `extract` refuses it (exit 6), so later runs don't try it again. Retrying a
rejected file is out of scope for this version.

## 3. Source (`S-###`)

One file per original: `10-sources/extracted/S-###.md`.

### 3.1 Front matter

The standard fields (`id`, `type: source`, `title`, `status`, `origin`, `confidence`,
`confidence_reason`, `inference_confirmed`, `audience`, `supports`, `contradicts`,
`derived_from`, `supersedes`, `clarifies`, `change_reason`, `change_trigger`, `created`)
are unchanged from 001/002. Source fields follow:

| Field | Values | Set by | Rule |
|---|---|---|---|
| `material` | `document` · `meeting-transcript` · `meeting-notes` | assistant (the script suggests `meeting-transcript` when it parses turns) | Required (FR-018) |
| `source_type` | `pdf` · `docx` · `markdown` · `text` · `vtt` · `srt` · `deck` · `spreadsheet` · `image` · `web` · `other` | script | File format. The last five are reserved for later versions. |
| `raw_file` | path relative to `10-sources/raw/` | script | Required, unique across sources |
| `raw_sha256` | 64 hex characters, or `""` for a restricted record | script | Unique across sources |
| `raw_bytes` | integer, the original's size from `stat` | script (`extract` and `register-restricted`) | Required. Used to flag possible copies of restricted files. |
| `provided_by` | text | assistant | Required, unless the consultant doesn't know (then `"not stated"`) |
| `source_date` | `YYYY-MM-DD`, `YYYY-MM`, `YYYY` or `""` | assistant | The document's date, or the meeting date |
| `meeting_title` | text | assistant | Meetings only. Shared by a transcript and a summary of the same meeting. |
| `meeting_date` | `YYYY-MM-DD` | assistant | Required when `material` is a meeting (FR-018) |
| `attendees` | list of names | assistant | Meetings, when known |
| `author` | text | assistant | Required for `meeting-notes` |
| `author_kind` | `person` · `ai-notetaker` | assistant | Required for `meeting-notes` |
| `extraction_status` | `in-progress` · `complete` | script | `complete` only through `finalize` (R12) |
| `fidelity` | `pending` · `checked` · `unchecked` · `""` (restricted) | script | `checked`: the word-for-word comparison ran and passed at `finalize`. `unchecked`: a PDF whose text the assistant copied because poppler was missing (R4). Set by `extract` (`unchecked` or `pending`) and by `finalize` (`checked`). |
| `extraction_method` | `text` · `ocr` · `vision-description` · `mixed` · `none` | script sets `text`. The assistant changes it when it adds OCR or descriptions. | `none` if and only if `restricted` and nothing was extracted |
| `derived` | boolean | assistant | `true` if and only if the content contains a `[!derived]` callout |
| `restricted` | boolean | script | `true` for records made by `register-restricted` or `restrict` |
| `content_removed` | boolean | script | `true` only after `restrict --remove-content` |
| `page_count` | integer | script (checked mode) or assistant from Read (unchecked mode) | PDFs only |
| `pages_reviewed` | integer, from 0 to `page_count` | assistant | PDFs only. Must equal `page_count` before `finalize`. |
| `uncertain_passages` | list of locators | assistant and script | Every entry must also be a line in `## Uncertain passages`, and the other way round |

Standard field rules for sources:

| Field | Rule |
|---|---|
| `status` | `proposed` when written (FR-022). Changes only through `set-status`. |
| `audience` | Always `internal`. `verify` reports `client-ready` as a problem. |
| `origin` | Suggested from `material` (§3.2): `client-document`, `interview-meeting` or `consultant-note`. The consultant may override it with `external-research` or `prior-engagement` (FR-019). Never `llm-inference`. |
| `confidence` | `high` · `medium` · `low`. Defaults to `medium`, with the reason "trust not stated by the consultant" (FR-020). Never `high` when `author_kind: ai-notetaker`. |
| `confidence_reason` | One line, required |
| `title` | Uses the client code name when one is set (FR-024) |
| `supersedes` | Set only after the consultant confirms a new version (FR-028) |

### 3.2 Origin suggested from material (FR-019)

| Material | Who wrote it | Origin |
|---|---|---|
| `document` | client | `client-document` |
| `meeting-transcript` | anyone | `interview-meeting` |
| `meeting-notes` | someone other than the consultant (a colleague, the client, an AI note-taker) | `interview-meeting` |
| `meeting-notes` or `document` | the consultant themselves | `consultant-note` |

### 3.3 Body

The full format, with examples, is in [contracts/source-file.md](contracts/source-file.md).

| Section | Holds | Written by |
|---|---|---|
| `## Context` | The consultant's line of context: who provided it, when, why it matters, how far to trust it | assistant, in the consultant's words |
| `## Description` | Up to three sentences on what the source is, labelled "Written by `ingest`. Not part of the source." No conclusions (FR-021). | assistant |
| `## Speakers` | Transcripts only: a table of the original label and the confirmed name | script (labels); assistant (names) |
| `## Uncertain passages` | `- <locator> — <why>`, one per passage | script and assistant |
| `## Extracted content` | Verbatim content between `<!-- cairn:content:start -->` and `<!-- cairn:content:end -->` | script, plus callouts and PDF tables from the assistant |

A restricted record has the first four sections (Speakers empty), and its content region
holds one line: `Restricted: not extracted. Do not open the original with an AI tool.`

### 3.4 Locators (FR-011)

| Format | Locator | Marker in the content |
|---|---|---|
| PDF | `p. 7` (PDF page number) | `### p. 7`, or `### p. 7 (printed: iv)` |
| Word, markdown | heading path, `§ Background > Scope`, plus `¶ 3` where a section has no headings | The original headings. `[¶3]` prefix where needed. |
| Plain-text document | `¶ 12` | `[¶12]` prefix |
| Transcript with timestamps | `00:14:32` (turn `T17` also accepted) | `**<label>** [T17 · 00:14:32]:` |
| Transcript without timestamps | `T17` | `**<label>** [T17]:` |
| Word comment | `comment 3 @ § Background` | `> [!comment] 3 · <author> · <date> · § Background` |

### 3.5 State transitions

```text
                extract                        finalize (verify passes)
 (original) ───────────────▶ in-progress ─────────────────────────────▶ complete, proposed
                                │                                           │
                         extract --restart                     set-status active ──▶ active
                         (same ID, rewritten)                  set-status rejected ─▶ rejected
                                                                            │
                                    approve a source that supersedes it ────▶ superseded
 (original) ── register-restricted ──▶ complete, proposed, restricted, method none

 any complete source ── restrict ──▶ restricted: true  (── --remove-content ──▶ content_removed: true)
```

- Only `finalize` sets `complete`, and only `finalize` adds the index row.
- An in-progress source can be rejected (for example, a PDF that Read can't open). It
  gets no index row, and its ID isn't reused. Its original then has state `rejected`, and
  `extract` refuses it (exit 6).
- `active`, `rejected` and `superseded` happen only through `set-status`, run after the
  consultant's explicit instruction *(assistant)* (FR-030, SC-008).
- Nothing ever sets `audience: client-ready` (FR-022).
- A source is never deleted, and an ID is never reused.

## 4. Source index row

`10-sources/index.md`, one row per complete source, in ID order:

```text
| S-004 | Operations review FY25 (Northwind) | document | 2026-10-14 | client-document | proposed | no |
```

| Column | From |
|---|---|
| ID | `id` |
| Title | `title` (code name, never the real name). A `\|` is escaped. |
| Type | `material` |
| Date | `source_date`, or `meeting_date` for meetings |
| Origin | `origin` |
| Status | `status` |
| Restricted | `yes` / `no` |

Only `finalize`, `set-status` and `restrict` write rows. `verify` reports a row that
disagrees with its source (`index-mismatch`), or a complete source with no row
(`index-missing`).

## 5. Speaker turn

| Attribute | Rule |
|---|---|
| label | The speaker as written in the original. Never changed. `(unlabelled)` when the original has none. |
| turn | `T1`, `T2`, … in order |
| timestamp | The first cue's start time, `hh:mm:ss` (milliseconds dropped from the marker only) |
| text | The words of every merged cue, in order, joined by single spaces |
| confirmed name | In `## Speakers`, never in the turn |

## 6. Derived and corrected passages

| Callout | Kind | Rule |
|---|---|---|
| `> [!derived] ocr` | Text read from a page image | Sets `derived: true`. `extraction_method` becomes `ocr` or `mixed`. |
| `> [!derived] vision-description` | Text read from a chart, diagram or photo, plus a description | Both parts go in the same callout, labelled "Text in image:" and "Description:" (constitution Skill Contract) |
| `> [!derived] chart-data` | A Word chart's cached data, as a table (script) | The assistant adds the description below it |
| `> [!derived] diagram-text` | Word SmartArt text (script) | |
| `> [!corrected] <date>` | A fixed passage. Lines: `was: …`, then the new text. | Logged as `extraction-fix` (§7). `verify` uses the `was:` text (R11). |

## 7. Change events written by ingest

Format per the shared convention: `YYYY-MM-DD · <subject> · <event> · <reason> · <trigger>`.

| Event | Subject | Trigger | Detail (`> ` lines) | Written by |
|---|---|---|---|---|
| `extraction-fix` | `S-004 @ p. 3` | `-` | Required: the previous text | assistant |
| `restrict` | `S-004` | `-` | Optional | script `restrict` |
| `remove-content` | `S-004` | `-` | Required: "content removed on instruction of <name>" | script `restrict --remove-content` |
| `supersede` | `S-002 → S-007` | as given by the consultant (usually `new evidence`) | Optional | script `set-status` |
| `reject` | `S-004` | as given | Optional | script `set-status` |

Approving a source (`active`) isn't logged, just as approving a charter item isn't
(002 convention).

## 8. Validation rules (`verify` problem codes)

| Code | Meaning |
|---|---|
| `missing-field` | A required field is empty (§3.1) |
| `bad-value` | A value isn't in its allowed set |
| `client-ready` | `audience` isn't `internal` |
| `confidence-cap` | `high` with `author_kind: ai-notetaker` |
| `derived-flag` | `derived` disagrees with the callouts present |
| `method-mismatch` | `extraction_method` disagrees with the callouts present, or is `none` on an unrestricted source |
| `uncertain-mismatch` | `uncertain_passages` and `## Uncertain passages` disagree |
| `content-mismatch` | The content differs from the original at a locator (R11). Checked sources only. |
| `fidelity-unchecked` | Warning: a PDF whose text was copied by the assistant without poppler. It can't be compared word for word, so spot-check it in review. |
| `markers-missing` | The content markers or a page marker are missing |
| `pages-incomplete` | `pages_reviewed` < `page_count` at `finalize` |
| `duplicate-id` · `malformed-id` | As in charter |
| `duplicate-original` | Two sources share a `raw_file` or a `raw_sha256` |
| `original-missing` | `raw_file` no longer exists. This is a warning: the record is kept. |
| `real-name-leak` | The real client name appears outside the content region (file and section only) |
| `index-mismatch` · `index-missing` | §4 |
| `restricted-has-content` | Warning: `restricted: true` and the content is still there (restricted after ingest, content not removed). Later skills must not read it. |
| `broken-link` | `supersedes` names a source that doesn't exist |
