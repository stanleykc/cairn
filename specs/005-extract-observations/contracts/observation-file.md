# Contract: Observation file (`O-###.md`)

What `extract-observations` writes, and what `triage`, `synthesize`, `test-hypothesis`,
`find-contradictions` and `what-changed` can rely on. Fields: [data-model §1](../data-model.md#1-observation-o).

## Guarantees to later skills

1. One file, one claim, one source. `source` is an existing `S-###`; `locator` resolves
   to a unit (and table row) of that source (data-model §3).
2. The `## Passage` text is a contiguous, word-for-word piece of the source's content
   region at the locator (whitespace and markdown markers normalised). It never comes from
   Context, Description, Speakers or Uncertain passages.
3. `derived: true` exactly when the passage lies in derived content. `speaker` is set for
   every transcript observation.
4. `origin` equals the source's origin and is never `llm-inference`. `confidence` never
   exceeds the source's, is ≤ `medium` for AI-written notes and `low` under an uncertain
   passage, and always has a reason.
5. `questions` holds only IDs that existed when written. Link fields are empty.
6. Written as `status: proposed`, `audience: internal`, in `_inbox/`. IDs are never reused.
7. After `tag`, only `questions` changed, and the change is in the changelog.

`observe.py verify` checks 1–6 on demand; later skills may run it before relying on an
observation.

## Skeleton (from a PDF table)

~~~markdown
---
id: "O-015"
type: observation
title: "North 2 averages 3.9 days to ship"
status: proposed
origin: client-document
confidence: medium
confidence_reason: "client's own KPI table; method not stated"
inference_confirmed: false
audience: internal
supports: []
contradicts: []
derived_from: []
supersedes: []
clarifies: []
change_reason: ""
change_trigger: ""
created: "2026-11-12"
source: "S-003"
locator: "p. 2 › table 1 › row 2 › Avg days to ship"
questions: ["Q-003"]
derived: false
speaker: ""
passage_kind: table-row
translated: false
---

## Claim

The FY25 operations review gives North 2's average days to ship as 3.9.

## Passage

> | North 2 | 38,950 | 3.9 |
~~~

## From a chart description (derived)

~~~markdown
locator: "p. 2"
derived: true
passage_kind: text
---

## Claim

The chart description on p. 2 says days to ship at both northern sites flatten in Q4.

## Passage

> Line chart with two lines (North 1, North 2) rising from about 2.5 to about 4 days
> between Q1 and Q3, then flattening in Q4.
~~~

The passage is the whole sentence that holds the claim; the script matches it across the
callout's line break.

## From meeting notes by an AI note-taker

~~~markdown
origin: interview-meeting
confidence: medium
confidence_reason: "AI note-taker summary, capped at medium"
---

## Claim

The AI notes by MeetBot report that the team agreed to pilot a second shift at North 2.

## Passage

> Team agreed to pilot a second shift at North 2 starting in January.
~~~
