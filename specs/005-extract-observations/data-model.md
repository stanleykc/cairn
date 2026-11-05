# Data Model: Extract Observations Skill

Entities, fields and rules for `extract-observations`. Research decisions are cited as R#.
All examples are synthetic.

## 1. Observation (`O-###`)

One file per observation: `_inbox/O-###.md` when written by the skill. The consultant (or
`triage`, later) moves it to `30-observations/`. Status lives in front matter, so moving it
changes nothing else.

### 1.1 Template change (`_templates/observation.md`, R4, R15)

Added fields, after `derived`:

```yaml
speaker: ""               # transcripts only: confirmed name, else the original label
passage_kind: ""          # text | table-row | comment | tracked-change
translated: false         # true when the claim is an English rendering of a non-English passage
```

New body (replaces the one-line placeholder):

```markdown
## Claim

One claim, from one source, with no interpretation.

## Passage

> The exact words from the source at the locator.
```

### 1.2 Fields as written by the skill

| Field | Value | Set by |
|---|---|---|
| `id` | next free `O-###` (R8) | script |
| `type` | `observation` | script |
| `title` | short, ≤ 80 characters, code name if in use | assistant |
| `status` | `proposed` | script |
| `origin` | the source's origin; never `llm-inference` (FR-014) | script |
| `confidence` | `high`/`medium`/`low`, ≤ cap (§1.3) | assistant, checked |
| `confidence_reason` | one line; prefixed `uncertain extraction: ` under an uncertain passage | assistant, checked |
| `inference_confirmed` | `false` | script |
| `audience` | `internal` | script |
| `supports`, `contradicts`, `derived_from`, `supersedes`, `clarifies` | `[]` (FR-018) | script |
| `change_reason`, `change_trigger` | `""` | script |
| `created` | today | script |
| `source` | `S-###` | assistant, checked |
| `locator` | per §3 | assistant, checked |
| `questions` | existing `Q-###` only (FR-017) | assistant, checked |
| `derived` | quote inside `[!derived]` (or derived `[!corrected]`) | script |
| `speaker` | transcript turns only (§1.4) | script |
| `passage_kind` | where the quote lies (R6) | script |
| `translated` | assistant's flag | assistant |
| `## Claim` | one sentence | assistant |
| `## Passage` | the quote, word for word, as `> ` lines | assistant, checked |

### 1.3 Confidence cap (FR-015, R6)

`cap = min(source.confidence, medium if source.author_kind == ai-notetaker, low if the
locator falls on an entry of source.uncertain_passages)`, ordered `low < medium < high`. A
draft above the cap is refused (`confidence-cap`).

### 1.4 Wording rules by material (FR-013, instructions; warnings in §5)

| Source material / passage | Claim form |
|---|---|
| `document`, text or table | The claim as the document states it: "The FY25 review gives North 2's average days to ship as 3.9." |
| `meeting-transcript` | "<speaker> said …", keeping hedges: "said they think", "estimated", "suspects" |
| `meeting-notes` | "The summary by <author> reports …" (or "The AI notes by <tool> report …") |
| `comment` | "A reviewer comment by <author> asks/says …" |
| `tracked-change` | "An unaccepted tracked change would make the text say …" |
| `translated: true` | Claim in English, followed by "(translated)" |

### 1.5 Example

```markdown
---
id: "O-014"
type: observation
title: "Warehouse manager says sales sends orders late"
status: proposed
origin: interview-meeting
confidence: medium
confidence_reason: "first-hand opinion about another team; not backed by data in the call"
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
source: "S-004"
locator: "00:12:41"
questions: ["Q-003"]
derived: false
speaker: "Dana Reyes"
passage_kind: text
translated: false
---

## Claim

Dana Reyes said that sales always sends orders to the warehouse late.

## Passage

> Honestly, sales always sends the orders late, that's the whole problem.
```

### 1.6 State transitions

```text
 add (drafts accepted) ──▶ _inbox/O-###.md, proposed
 consultant / triage ────▶ active | rejected (reason, trigger) ; moved to 30-observations/
 tag (on confirmation) ──▶ questions += [Q-###], claim unchanged, changelog `tag`
```

The skill never sets `active`, `rejected`, `superseded` or `client-ready` (FR-019, SC-008).

## 2. Draft and drafts file (R2, R11)

The assistant writes `.cairn/work/extract-observations/drafts-<S-ID>-<n>.json` and passes
it to `add`. It is a working file, not a record; it can be deleted after `add`.

```json
{
  "steering": {
    "focus": ["Q-003"],
    "exclude": ["§ Appendix"],
    "perspective": "warehouse manager"
  },
  "drafts": [
    {
      "source": "S-004",
      "locator": "p. 2 › table 1 › row 2 › Avg days to ship",
      "quote": "| North 2 | 38,950 | 3.9 |",
      "claim": "The FY25 operations review gives North 2's average days to ship as 3.9.",
      "title": "North 2 averages 3.9 days to ship",
      "questions": ["Q-003"],
      "confidence": "medium",
      "confidence_reason": "client's own KPI table; method not stated",
      "translated": false
    }
  ]
}
```

| Field | Rule |
|---|---|
| `steering.focus` | existing question IDs, or `[]` |
| `steering.exclude` | locator prefixes, page ranges `p. a–b`, or `speaker: <label or name>` |
| `steering.perspective` | free text or `""` |
| `source`, `locator`, `quote`, `claim`, `title`, `confidence`, `confidence_reason` | required, non-empty |
| `questions` | list; with a non-empty `focus`, must share at least one ID with it |
| `translated` | optional, default `false` |
| `accept_warnings` | optional list of warning codes the assistant accepts for this draft (§5) |

## 3. Locator (FR-011, R5)

```text
locator  = unit [ " › table " n " › row " m [ " › " column-header ] ]
unit     = "p. " page                        # PDF
         | "§ " heading { " > " heading } [ " ¶ " n ]   # Word, markdown
         | "¶ " n                            # plain text
         | hh ":" mm ":" ss | "T" n          # transcript turn
         | "comment " n " @ " heading-path   # Word comment
```

- `unit` is exactly an `ingest` locator (003 data-model §3.4).
- Tables are counted from 1 within the unit; rows from 1 among data rows. A column, when
  given, must match a header cell.
- A table locator is **required** when the quote is a table row (US1-8): `add` refuses a
  bare page locator for a quote that lies in a table (`table-locator-missing`).

## 4. Progress record (R12)

`.cairn/work/extract-observations/progress.json`:

```json
{
  "S-004": {
    "state": "stopped",
    "stopped_at": "p. 18",
    "steering": {"focus": [], "exclude": ["§ Appendix"], "perspective": ""},
    "updated": "2026-11-12"
  },
  "S-002": {"state": "done", "updated": "2026-11-11"}
}
```

| `state` | Meaning |
|---|---|
| `stopped` | a natural break; resume after `stopped_at` |
| `done` | a full pass was completed (with the steering recorded) |

It is a convenience, not a record of evidence: if it is lost, `prepare` still lists the
existing observations, and nothing is duplicated (R9).

## 5. Check codes (`add` and `verify`)

Refusals (the draft is not written):

| Code | Meaning |
|---|---|
| `policy-unconfirmed` | `model_use: unconfirmed` (exit 3, whole run) |
| `source-restricted` | restricted or content removed (exit 3) |
| `source-unknown` · `source-incomplete` | no such source, or `extraction_status: in-progress` |
| `source-retired` | `rejected`/`superseded` source without `--confirmed` |
| `source-llm-inference` | the source's origin is `llm-inference` |
| `missing-field` · `bad-value` | a required draft field is empty, or a value isn't allowed |
| `locator-unknown` | no such unit, table, row or column in the source |
| `quote-not-found` | the quote isn't a contiguous substring of the unit/row |
| `quote-outside-content` | the quote is only found in Context, Description, Speakers or Uncertain passages |
| `quote-too-short` | under 3 words (table rows exempt) |
| `table-locator-missing` | a table-row quote with a bare unit locator |
| `confidence-cap` | confidence above the cap (§1.3) |
| `question-unknown` | a tag or focus ID that doesn't exist in `00-charter/questions.md` |
| `off-focus` | with a focus, the draft shares no ID with it |
| `excluded` | the locator lies in an excluded part |
| `duplicate` | same source, passage and claim as an existing observation |
| `previously-rejected` | as `duplicate`, and the match is `rejected` |
| `real-name-leak` | the real client name in `title` or `claim` while a code name is in use |
| `client-ready` | a `status: proposed` observation with `audience` other than `internal` (`verify` only; the consultant may set `client-ready` on observations they have made `active`) |

Warnings (refused unless listed in the draft's `accept_warnings`):

| Code | Meaning |
|---|---|
| `same-passage` | another observation quotes an overlapping passage of the same source |
| `attribution-missing` | a transcript claim that doesn't name the speaker |
| `summary-attribution-missing` | a meeting-notes claim that doesn't name the author or say "summary"/"notes" |
| `kind-unstated` | a comment or tracked-change claim that doesn't say so |
| `source-not-approved` | informational: the source is still `proposed` (never refuses) |
| `question-retired` | the tagged question is `superseded` or `rejected` |

`verify [O-ID …]` re-runs every check except `duplicate`/`same-passage` against the
observation as stored, and also reports `broken-link` (a link field names an ID that
doesn't exist) and `status-invalid` (a status or audience outside the allowed values).
A hand-written observation with no `## Passage` gets the warning `passage-missing`, not an
error; the new template fields default to empty, so older observations still pass.

## 6. Change event: `tag` (R10)

Added to the shared change convention and the changelog seed:

| Event | When | Subject | Trigger | Detail |
|---|---|---|---|---|
| `tag` | A question tag is added to an existing observation, on the consultant's confirmation | `O-012` | `-` | optional |

```text
2026-11-12 · O-012 · tag · added Q-006 · -
```

The reason is `added <Q-ID>[, <Q-ID>]`. One line per observation per run.

## 7. Entities read, not written

| Entity | Read from | Used for |
|---|---|---|
| Engagement | `engagement.md` (script only) | `model_use`, `client_label`, real name for the leak check |
| Source `S-###` | `10-sources/extracted/S-###.md` | gates, origin, confidence, `author_kind`, `uncertain_passages`, `## Speakers`, content region |
| Question `Q-###` | `00-charter/questions.md` | valid tags and focus; titles shown in the summary |
| Stakeholder | `00-charter/stakeholders.md` | matching a perspective name to speakers (assistant) |
| Existing observations | `_inbox/`, `30-observations/` | duplicates, rejected claims, retagging, IDs |
