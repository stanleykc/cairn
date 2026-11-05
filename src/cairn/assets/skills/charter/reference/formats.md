# Formats: what the charter files look like

Filled examples of everything `charter` writes. The names are synthetic. Always copy the
field list from the engagement's own `_templates/<type>.md` and fill it in as shown here.
The examples use today's date as `2026-11-03`; write the real date.

## Rules for every entry

- Take the ID from `next_ids` in `charter.py status`. Run `status` again before each new
  ID. Never reuse a number, even when an entry was deleted by hand.
- Append new entries at the **end** of the file. The first entry replaces the
  "No questions yet." / "No hypotheses yet." / "No assumptions yet." line.
- Write lists inline, with quoted IDs: `["Q-001", "Q-002"]`. An empty list is `[]`.
- New entries are always `status: proposed`, `audience: internal`,
  `inference_confirmed: false`, `change_reason: ""`, `change_trigger: ""`.
- `origin` is `consultant-note` for anything from the consultant's answers, including their
  summary of the brief. It is `llm-inference` only for a suggestion the consultant kept
  (`reference/interview.md`, "Gap check and suggestions").
- `confidence` is `high`, `medium` or `low`, always with a one-line `confidence_reason`.
- Never write a source ID (`S-###`) in any field, and never `origin: client-document`.
- Keep the `# comments` from the template on each line.

## Question

````markdown
## Q-001: Why is order-to-ship slow in the north DCs

```yaml
id: "Q-001"        # permanent; next free number for this type, never reused
type: question
title: "Why is order-to-ship slow in the north DCs"
status: proposed          # proposed | active | superseded | rejected
origin: consultant-note   # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: high          # high | medium | low
confidence_reason: "Raised by the sponsor at kickoff"     # one line
inference_confirmed: false  # consultant sets true after checking an llm-inference item against a source
audience: internal        # internal | client-ready (only the consultant sets client-ready)
supports: []              # IDs
contradicts: []           # IDs
derived_from: []          # IDs
supersedes: []            # IDs
clarifies: []             # IDs
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "2026-11-03"
priority: high            # high | medium | low
raised_by: "Pat Sponsor"
hypotheses: ["H-001"]     # H-IDs
```

Why is order-to-ship time in the north DCs above target? The sponsor's main objective
depends on it.
````

- `title`: short, about ten words or fewer. The same text goes in the heading.
- `priority`: as the consultant gives it. Leave `""` if they don't say.
- `raised_by`: who asked it (a stakeholder or the consultant).
- `hypotheses`: starts `[]`. Each time a hypothesis for this question is written, add its
  H-ID here **in the same step**, so the link is written in both directions at once.
- Body: the question in one or two sentences, and why it matters to the client.

## Hypothesis

````markdown
## H-001: Slotting rules are the bottleneck

```yaml
id: "H-001"        # permanent; next free number for this type, never reused
type: hypothesis
title: "Slotting rules are the bottleneck"
status: proposed          # proposed | active | superseded | rejected
origin: consultant-note   # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: low           # high | medium | low
confidence_reason: "Consultant hunch from prior fulfillment work"     # one line
inference_confirmed: false  # consultant sets true after checking an llm-inference item against a source
audience: internal        # internal | client-ready (only the consultant sets client-ready)
supports: []              # IDs
contradicts: []           # IDs
derived_from: []          # IDs
supersedes: []            # IDs
clarifies: []             # IDs
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "2026-11-03"
question: "Q-001"         # Q-ID
confirm_if: "Pick travel time is over 40% of order cycle time in the north DCs"   # evidence that would confirm it
reject_if: "Pick travel time is under 20% of order cycle time"   # evidence that would reject it
supported_by: []          # O/F-IDs
contradicted_by: []       # O/F-IDs
```

The warehouse slotting rules are the main cause of slow order-to-ship time.
````

- `question`: exactly one existing Q-ID, quoted. Never write a hypothesis without one.
- `confirm_if` / `reject_if`: one line each, in the consultant's words. Ask for both. If the
  consultant declines, leave `""`; `status` then reports it as a gap.
- `supported_by` / `contradicted_by` stay `[]`: linking evidence is a later skill's job.
- Body: the working hypothesis in one sentence.

## Assumption

````markdown
## A-001: Volumes stay near last year

```yaml
id: "A-001"        # permanent; next free number for this type, never reused
type: assumption
title: "Volumes stay near last year"
status: proposed          # proposed | active | superseded | rejected
origin: consultant-note   # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: medium        # high | medium | low
confidence_reason: "Consistent with what the client said at kickoff"     # one line
inference_confirmed: false  # consultant sets true after checking an llm-inference item against a source
audience: internal        # internal | client-ready (only the consultant sets client-ready)
supports: []              # IDs
contradicts: []           # IDs
derived_from: []          # IDs
supersedes: []            # IDs
clarifies: []             # IDs
change_reason: ""         # one line: reason for the latest supersede or reject
change_trigger: ""        # new-evidence | client-feedback | rethinking
created: "2026-11-03"
basis: "Client planning forecast, as summarized by the consultant"
questions: ["Q-001"]      # Q-IDs
```

Order volumes stay within 10% of last year through December. If they spike, the baseline
measurements will not be comparable.
````

- `basis`: why the consultant takes it as true, in one line.
- `questions`: the Q-IDs it affects (may be `[]`).
- Body: the assumption in one sentence, and what happens to the work if it is false.

## Scope (`00-charter/scope.md`)

The first fill of a section **replaces** its seed guidance sentence (for example "What the
client needs from this engagement, in a few bullet points."). Keep the front matter and
the `## Model use` section as they are: only `charter.py model-use` changes model use.

```markdown
## Objectives

- Cut order-to-ship time by 30% in the north DCs.
- Recommend a fulfillment operating model the client can run without new headcount.

## Boundaries

What is in scope and, just as important, what is not.

### In scope

- The three north-region distribution centers.

### Out of scope

- Inbound supplier logistics.

## Deliverables

- Diagnostic readout — slide deck — due 2026-11-20
- Final recommendations — report and deck — due date TBD

## Timeline

- 2026-11-03 — Kickoff
- 2026-12-04 — Final readout

## Constraints

- **Budget**: no capital spend on new automation this fiscal year.
- **Politics**: the north DC leads were not consulted in the last review.
```

- Deliverables: `<deliverable> — <form> — due <YYYY-MM-DD or "date TBD">`.
- Timeline: `<YYYY-MM-DD or week> — <milestone>`.
- Constraints: one bullet each, starting with **Budget**, **Timeline**, **Technology**,
  **Politics** or **Other**.
- Leave the `## Boundaries` guidance sentence in place; fill the two `###` sections.
- Replacing a section that was filled in an **earlier** session is a scope change: rewrite
  the whole section and log `scope-change` (`reference/change-convention.md`).

### Upgrading an older `scope.md`

Engagements created with framework 0.1.0 have an older `scope.md`. The first time you
write to it in a session:

- Add any missing front matter lines after `model_use:`, in this order:
  `charter_status: draft  # draft | approved`, `approved_on: ""`, `approved_by: ""`. Do not
  add `model_use_notes` by hand: `charter.py model-use` adds it.
- Add `### In scope` and `### Out of scope` under `## Boundaries`, moving nothing that is
  already written there.
- Add `## Constraints` directly before `## Model use`.
- Never edit the Model use section by hand.

## Stakeholder row (`00-charter/stakeholders.md`)

```markdown
| Pat Sponsor | VP Operations, sponsor | Wants faster shipping before peak | not yet interviewed |
```

- Columns: Name, Role, Perspective, Interview status.
- Interview status: `not yet interviewed` (default), `scheduled` or `interviewed`.
- Write a literal `|` inside a cell as `\|`.
- Append rows at the end of the table. Change an existing row only when the consultant
  asks.
- Sensitive notes (credibility, politics) go into Perspective only after the consultant
  confirms they should be written.

## Lens and criterion bullets (`00-charter/lenses.md`)

```markdown
## Lenses

- **Cost**: cost to serve per order and the cost of each change.
- **Risk**: operational and delivery risk, especially during peak.

## Evaluation criteria

- **Time to value**: benefit visible within one quarter.
```

- One bullet each: `- **<Name>**: <one-line description>`.
- Names are unique within a section, ignoring case.

## Changelog line (`60-log/changelog.md`)

The full rules are in `reference/change-convention.md`. Shape:

```text
2026-11-10 · H-002 → H-004 · supersede · narrowed to inbound receiving only · new evidence
2026-11-10 · A-001 · reject · carriers confirmed SLA penalties apply · client feedback
2026-11-10 · scope/Timeline · scope-change · readout moved by sponsor · client feedback
> - 2026-12-04 — Final readout
2026-11-03 · charter · approve-charter · approved by Test Lead · -
```

Append newest last. The first event replaces the "No changes yet." line. `model-use`
events are written by `charter.py model-use`, never by hand.

## Items drawn from a document

When the consultant confirmed an answer you drafted from a document
(`reference/interview.md`, "Drafting from a document"):

- **Q, H and A entries.** `origin` stays `consultant-note`. Never cite a source ID
  (`S-###`) and never write `origin: client-document`. If the item was confirmed as
  drafted or lightly edited, `confidence_reason` starts with
  `From <document name>, confirmed by the consultant`, for example
  `"From sow-2026-10.pdf, confirmed by the consultant; dates match the signed SOW"`. If the
  consultant rewrote it in their own words, write an ordinary reason.
- **`<document name>`** is the file name relative to `10-sources/raw/` (as `doc` returned
  it in `document`), or `pasted text (<the consultant's description>)`.
- **Scope, stakeholders and lenses** have no per-item provenance field. After saving the
  topics drawn from a document, append one changelog line per document used in the
  session, listing those topics (append again for topics drawn later):

```text
2026-11-05 · charter · drew Objectives, Boundaries, Deliverables, Timeline from sow-2026-10.pdf (consultant confirmed)
```

  This line records provenance; it is not a change event, so it has no reason or trigger.
  Separate topics with commas, never with ` · `.
