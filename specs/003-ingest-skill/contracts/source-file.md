# Contract: Extracted source file (`10-sources/extracted/S-###.md`)

What `ingest` writes, and what `extract-observations` and every later skill can rely on.
Field rules are in [data-model §3](../data-model.md#3-source-s). All examples are
synthetic.

## Guarantees to later skills

1. Everything between `<!-- cairn:content:start -->` and `<!-- cairn:content:end -->` is
   the original's text, word for word, except inside `[!derived]` callouts (produced by
   the skill), `[!corrected]` callouts (fixed by the consultant, with the previous text
   kept) and locator markers.
2. Every passage in the content region has a locator ([data-model §3.4](../data-model.md#34-locators-fr-011)).
   An observation cites `source: "S-###"` and `locator: "<locator>"`. It sets
   `derived: true` when it cites text inside a `[!derived]` callout.
3. `## Context` and `## Description` are not evidence. Observations must not cite them.
4. A source with `restricted: true` must not be read by any skill, whatever its content
   region holds.
5. A source with `extraction_status: in-progress` is not finished. Later skills skip it.
6. `fidelity: checked` means the content was proven word for word against the original.
   `fidelity: unchecked` (a PDF ingested without poppler) means it was copied by the
   assistant and only spot-checked. Later skills may cite it, but they should tell the
   consultant when a key claim rests on an unchecked source.

## Skeleton

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

## Per-format content

**Word** keeps its own headings, so locators are heading paths. Comments follow the main
text, and tracked changes stay inline:

~~~markdown
<!-- cairn:content:start -->
# Process manual

## Receiving

Pallets are checked against the ASN {++within two hours++} on arrival.

> [!derived] chart-data
> **Chart:** Dock wait time by shift
> | Shift | Minutes |
> |---|---|
> | Early | 34 |
> | Late | 51 |
> **Description:** Bar chart; the late shift waits about half again as long.

<!-- cairn:comments -->
> [!comment] 1 · J. Ortiz · 2026-09-30 · § Process manual > Receiving
> Is this still true since the new dock schedule?
<!-- cairn:content:end -->
~~~

**Transcript** turns keep the original labels. Confirmed names go in `## Speakers` only:

~~~markdown
## Speakers

| Label | Confirmed name |
|---|---|
| Speaker 1 | Dana Reyes (stakeholders.md) |
| Speaker 2 | not confirmed |

## Extracted content

<!-- cairn:content:start -->
**Speaker 1** [T1 · 00:00:04]: Thanks for joining. Let's start with the north sites.

**Speaker 2** [T2 · 00:00:11]: Sure. The backlog really started in July, when we lost
two shift leads.
<!-- cairn:content:end -->
~~~

**Plain-text document** paragraphs are numbered, and line breaks are kept as hard breaks:

~~~markdown
<!-- cairn:content:start -->
[¶1] Notes from the site visit, 3 Oct.  
Weather delayed two inbound trucks.

[¶2] The supervisor said cycle counts are skipped on Fridays.
<!-- cairn:content:end -->
~~~

**Restricted record**:

~~~markdown
<!-- cairn:content:start -->
Restricted: not extracted. Do not open the original with an AI tool.
<!-- cairn:content:end -->
~~~

## Corrected passage

After review, a wrong OCR line becomes:

~~~markdown
> [!corrected] 2026-11-07
> was: Figures are taken from the VMS shipment log, excluding returns.
> Figures are taken from the WMS shipment log, excluding returns.
~~~

A `[!corrected]` callout replaces a whole passage (a paragraph, a turn, a table row or a
callout line). When the fixed text came from a `[!derived]` callout, the header is
`> [!corrected] 2026-11-07 · derived`, so the passage still counts as derived. The
changelog records the same previous text:

~~~text
2026-11-07 · S-003 @ p. 3 · extraction-fix · OCR misread WMS · -
> Figures are taken from the VMS shipment log, excluding returns.
~~~
