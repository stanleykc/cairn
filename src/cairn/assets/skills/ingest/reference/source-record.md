# The source record

One file per original: `10-sources/extracted/S-###.md`. `extract` writes it from
`_templates/source.md`; you fill the metadata and context. `verify` checks every rule here
unless it is marked *(assistant)*.

## Front matter

Standard fields (`id`, `type: source`, `status`, `origin`, `confidence`,
`confidence_reason`, `inference_confirmed`, `audience`, `supports`, `contradicts`,
`derived_from`, `supersedes`, `clarifies`, `change_reason`, `change_trigger`, `created`)
work as for every Cairn object. `title` is required.

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

Lists are written inline with quoted values: `uncertain_passages: ["p. 3", "§ Receiving"]`.

Standard fields, for sources:

| Field | Rule |
|---|---|
| `status` | `proposed` when written (FR-022). Changes only through `set-status`, on the consultant's explicit instruction. |
| `audience` | Always `internal`. `verify` reports `client-ready` as a problem. |
| `origin` | Suggested from `material` (below). The consultant may override it with `external-research` or `prior-engagement` (FR-019). Never `llm-inference`. |
| `confidence` | `high` · `medium` · `low`. Defaults to `medium`, with the reason "trust not stated by the consultant" (FR-020). Never `high` when `author_kind: ai-notetaker`. |
| `confidence_reason` | One line, required. Use the consultant's words about trust when they give them. |
| `title` | Uses the client code name (`client_label` from `status`) when one is set (FR-024) |
| `supersedes` | Set only after the consultant confirms that a file is a new version of an existing source (FR-028) |

### Origin from material (FR-019)

| Material | Who wrote it | Origin |
|---|---|---|
| `document` | client | `client-document` |
| `meeting-transcript` | anyone | `interview-meeting` |
| `meeting-notes` | someone other than the consultant (a colleague, the client, an AI note-taker) | `interview-meeting` |
| `meeting-notes` or `document` | the consultant themselves | `consultant-note` |

## Code name *(assistant, checked by `verify`)*

When `status` says `uses_code_name: true`, the title, `## Context`, `## Description`, the
index row and every log line use `client_label`, never the real client name. `verify`
reports `real-name-leak` (file and section only). The content region is the original's
text and is never changed, even when it names the client.

## Body

| Section | Holds | Written by |
|---|---|---|
| `## Context` | The consultant's line of context: who provided it, when, why it matters, how far to trust it | assistant, in the consultant's words |
| `## Description` | After the label `*Written by \`ingest\`. Not part of the source.*`, up to three sentences on what the source **is** (kind, length, what it covers), never what it shows. No conclusions (FR-021). | assistant |
| `## Speakers` | Transcripts only: `\| Label \| Confirmed name \|` | script (labels); assistant (names) |
| `## Uncertain passages` | `- <locator> — <why>`, one per passage | script and assistant |
| `## Extracted content` | Verbatim content between `<!-- cairn:content:start -->` and `<!-- cairn:content:end -->` | script, plus callouts and PDF tables from the assistant |

A restricted record has the first four sections (Speakers empty), and its content region
holds one line: `Restricted: not extracted. Do not open the original with an AI tool.`

## Locators (FR-011)

| Format | Locator | Marker in the content |
|---|---|---|
| PDF | `p. 7` (PDF page number) | `### p. 7`, or `### p. 7 (printed: iv)` |
| Word, markdown | heading path, `§ Background > Scope`, plus `¶ 3` where a section has no headings | The original headings. `[¶3]` prefix where needed. |
| Plain-text document | `¶ 12` | `[¶12]` prefix |
| Transcript with timestamps | `00:14:32` (turn `T17` also accepted) | `**<label>** [T17 · 00:14:32]:` |
| Transcript without timestamps | `T17` | `**<label>** [T17]:` |
| Word comment | `comment 3 @ § Background` | `> [!comment] 3 · <author> · <date> · § Background` |

## Callouts

| Callout | Kind | Rule |
|---|---|---|
| `> [!derived] ocr` | Text read from a page image | Sets `derived: true`. `extraction_method` becomes `ocr` or `mixed`. |
| `> [!derived] vision-description` | Text read from a chart, diagram or photo, plus a description | Both parts go in the same callout, labelled "Text in image:" and "Description:" (constitution Skill Contract) |
| `> [!derived] chart-data` | A Word chart's cached data, as a table (script) | The assistant adds the description below it |
| `> [!derived] diagram-text` | Word SmartArt text (script) | |
| `> [!corrected] <date>` | A fixed passage. Lines: `was: …`, then the new text. | Logged as `extraction-fix`. `verify` uses the `was:` text (R11). |

## What later skills can rely on

1. Everything between the content markers is the original's text, word for word, except
   inside `[!derived]` callouts, `[!corrected]` callouts and locator markers.
2. Every passage in the content region has a locator. An observation cites
   `source: "S-###"` and `locator: "<locator>"`, and sets `derived: true` when it cites
   text inside a `[!derived]` callout.
3. `## Context` and `## Description` are not evidence. Observations must not cite them.
4. A source with `restricted: true` must not be read by any skill.
5. A source with `extraction_status: in-progress` is not finished. Later skills skip it.
6. `fidelity: checked` means the content was proven word for word against the original;
   `fidelity: unchecked` means a PDF copied without poppler and only spot-checked.

## Example: a PDF source

~~~markdown
---
id: "S-003"
type: source
title: "Operations review FY25 (Northwind)"
status: proposed
origin: client-document
confidence: medium
confidence_reason: "trust not stated by the consultant"
inference_confirmed: false
audience: internal
supports: []
contradicts: []
derived_from: []
supersedes: []
clarifies: []
change_reason: ""
change_trigger: ""
created: "2026-11-06"
material: document
source_type: pdf
raw_file: "ops/ops-review-fy25.pdf"
raw_sha256: "9f2c…"
raw_bytes: 482113
provided_by: "COO office"
source_date: "2026-10-14"
meeting_title: ""
meeting_date: ""
attendees: []
author: ""
author_kind: ""
extraction_status: complete
fidelity: checked
extraction_method: mixed
derived: true
restricted: false
content_removed: false
page_count: 3
pages_reviewed: 3
uncertain_passages: ["p. 3"]
---

## Context

Sent by the COO's office on 2026-10-14 ahead of the kickoff. Their own view of FY25
performance. Treat the targets as aspirational.

## Description

*Written by `ingest`. Not part of the source.* A 3-page internal review of fulfilment
performance by distribution centre, with a KPI table and a trend chart.

## Speakers

| Label | Confirmed name |
|---|---|

## Uncertain passages

- p. 3 — scanned page; the last line of the footnote is faint

## Extracted content

<!-- cairn:content:start -->
### p. 1 (printed: i)

Operations Review FY25
Prepared for the executive team

### p. 2

Order-to-ship time rose in both northern sites during Q3.

| Site | Orders | Avg days to ship |
|---|---|---|
| North 1 | 41,200 | 3.4 |
| North 2 | 38,950 | 3.9 |

> [!derived] vision-description
> **Text in image:** "Days to ship, FY25" · Q1 · Q2 · Q3 · Q4
> **Description:** Line chart with two lines (North 1, North 2) rising from about 2.5 to
> about 4 days between Q1 and Q3, then flattening in Q4.

### p. 3

> [!derived] ocr
> Appendix: method. Figures are taken from the WMS shipment log, excluding returns.
> Note: Q4 figures are provisional and may be revised.
<!-- cairn:content:end -->
~~~
