# Data Model: Charter Skill

This feature writes the first real objects in an engagement. It uses the containers and
templates from feature 001 ([001 data model](../001-engagement-init/data-model.md)) and
makes the small changes listed in §1. Every rule here is checked by
`charter.py check` ([contracts/charter-script.md](contracts/charter-script.md)), unless it
is marked *(assistant)*.

## 1. Changes to the framework data model

| Change | Files | Why |
|---|---|---|
| New standard fields `change_reason: ""` and `change_trigger: ""` (`new-evidence` \| `client-feedback` \| `rethinking`), placed after `clarifies` | all 12 `assets/templates/*.md` | The reason and trigger stay on a superseded or rejected item (FR-024, FR-026). The same fields serve `record-change` for every type (FR-030, research R10). |
| New hypothesis fields `confirm_if: ""` and `reject_if: ""`, placed after `question` | `assets/templates/hypothesis.md` | FR-015, and the "no rejection condition" gap check (FR-031, R14) |
| New field `model_use_notes: ""` after `model_use` | `assets/seed/engagement.md` (with one line of body explanation) | Specific restrictions are stored in the authoritative record (FR-005, R8) |
| `scope.md` front matter gains `model_use_notes`, `charter_status: draft`, `approved_on: ""`, `approved_by: ""`. The body gains `### In scope` and `### Out of scope` under Boundaries, a `## Constraints` section, and a `Restrictions:` line under Model use | `assets/seed/00-charter/scope.md` | FR-005, FR-008, FR-035 (R15) |
| Guidance rewritten to the shared change convention | `assets/seed/60-log/changelog.md` | FR-028, FR-030 (R12) |
| Framework version `0.1.0` → `0.2.0` | `src/cairn/__init__.py` | Refresh delivers the skill and the new templates (R22) |

The 001 data-model doc (§3.1 standard fields, §3.2 hypothesis row, §2 record) and
`contracts/engagement-record.md` are updated in the same change, because the constitution
requires every template and document that uses the data model to move together.

Engagements created before this change don't get the new seed fields, because seed files
are never refreshed. The skill adds any missing `scope.md` or `engagement.md` field or
heading the first time it writes (§3, §4). Missing new standard fields in existing entries
are treated as empty. The skill adds them when it next changes that entry's status.

## 2. Charter

The engagement's framing: the six files in `00-charter/`.

| Attribute | Where | Values |
|---|---|---|
| `charter_status` | `scope.md` front matter | `draft` (default; also used when the field is missing) \| `approved` |
| `approved_on` | `scope.md` front matter | `YYYY-MM-DD` of the latest approval, or `""` |
| `approved_by` | `scope.md` front matter | name of the latest approver, or `""` |
| state (derived) | `charter.py status` | `empty` \| `draft` \| `approved` (R16) |

**Transitions**

~~~text
empty --first topic saved--> draft
draft --"approve charter" and model_use != unconfirmed--> approved   (every proposed item → active first, after the consultant confirms the list; logs approve-charter)
draft --"approve charter" and model_use == unconfirmed--> draft      (items may still go active; skill says why)
approved --revision--> approved                                      (summary counts items proposed since approved_on)
approved --"approve charter" again--> approved                       (approved_on/by updated; logs approve-charter)
~~~

## 3. Scope (`00-charter/scope.md`)

Not a numbered object. Sections, in order:

| Section | Content | Filled when |
|---|---|---|
| `## Objectives` | Bullets: what the client needs | Required for a draft (FR-009) |
| `## Boundaries` → `### In scope`, `### Out of scope` | Bullets | Optional |
| `## Deliverables` | Bullets: `<deliverable> — <form> — due <YYYY-MM-DD or "date TBD">` | Optional. A deliverable without a date is a gap *(assistant)*. |
| `## Timeline` | Bullets: `<YYYY-MM-DD or week> — <milestone>` | Optional |
| `## Constraints` | Bullets, each starting with **Budget**, **Timeline**, **Technology**, **Politics** or **Other** | Optional |
| `## Model use` | `Current policy: **<value>**.` · `Restrictions: <notes or "none recorded">.` · the standard explanation | Written by `charter.py model-use` only |

**Rules**

- The seed guidance sentence under a heading counts as empty. `status` recognizes the
  seed sentences from both framework versions. The first fill replaces the sentence.
- Once a section holds content written in an earlier session, replacing it is a
  scope change: the section is rewritten in full, and a `scope-change` event is logged,
  with the previous text in a quoted block (FR-027, FR-028).
- Front matter `model_use` and `model_use_notes` must equal `engagement.md`
  (check: `model-use-mismatch`).
- No section may contain the real client name when a code name is in use
  (check: `real-name-leak`).

## 4. Engagement record additions (`engagement.md`)

| Field | Type | Writer | Rule |
|---|---|---|---|
| `model_use` | `allowed` \| `restricted` \| `unconfirmed` | init, consultant, `charter.py model-use` | Authoritative. Unchanged from 001. |
| `model_use_notes` | string (double-quoted) | consultant, `charter.py model-use` | Free text: what may or may not be sent. `""` when none is recorded. If the line is missing, `model-use` adds it directly after `model_use:`. |

The assistant never reads this file (R7). `status` exposes `engagement_name`,
`client_label`, `uses_code_name`, `lead_consultant`, `model_use` and `model_use_notes`.

## 5. Question, hypothesis, assumption entries

Entry form, as defined by 001 (R16): an `## <ID>: <title>` heading, a fenced `yaml` block,
then the body. Files: `questions.md`, `hypotheses.md`, `assumptions.md`. New entries are
appended at the end of the file. The first one replaces the "No … yet." line.

### 5.1 Field values the skill writes

| Field | Question | Hypothesis | Assumption |
|---|---|---|---|
| `id` / heading | next free `Q-###` (R9) | next free `H-###` | next free `A-###` |
| `title` | short, ≤ ~10 words | short | short |
| `status` | `proposed` | `proposed` | `proposed` |
| `origin` | `consultant-note`, or `llm-inference` for a kept suggestion | same | same |
| `confidence` + `confidence_reason` | required; for suggestions the reason starts "Suggested by `charter`:" | same | same |
| `inference_confirmed` | `false` | `false` | `false` |
| `audience` | `internal` | `internal` | `internal` |
| `supports`, `contradicts`, `derived_from`, `clarifies` | `[]` | `[]` | `[]` |
| `supersedes` | `[]`, or `["<old ID>"]` for a new version | same | same |
| `change_reason`, `change_trigger` | `""`, or set for a new version (§6) | same | same |
| `created` | today | today | today |
| type-specific | `priority` (high/medium/low), `raised_by`, `hypotheses` (H-IDs) | `question` (exactly one Q-ID), `confirm_if`, `reject_if`, `supported_by: []`, `contradicted_by: []` | `basis`, `questions` (Q-IDs, may be empty) |
| body | The question in one or two sentences, and why it matters | The hypothesis in one sentence | The assumption in one sentence, and what happens if it is false |

The skill never writes a source ID or `origin: client-document` (FR-019). Lists are always
written inline, with quoted IDs: `["Q-001", "Q-002"]`.

### 5.2 Validation rules (`check` problem codes)

| Code | Rule | Source |
|---|---|---|
| `duplicate-id` | An ID appears as a heading more than once | edge case |
| `malformed-id` | A heading doesn't match `## <P>-<3+ digits>: <title>`, or the heading ID ≠ the `id` field, or the prefix ≠ the file's `holds` | edge case |
| `unparseable` | A `yaml` block can't be read (R4) | R4 |
| `missing-field` | A standard field from 001, or a type-specific field from 001, is missing. The fields added in 0.2.0 (`change_reason`, `change_trigger`, `confirm_if`, `reject_if`) are treated as empty when missing, so entries written by hand before 0.2.0 still pass. An empty `confirm_if` or `reject_if` is reported as a gap (§5.4), not a problem. | SC-003 |
| `bad-value` | `status`, `origin`, `confidence`, `audience`, `priority` or `change_trigger` is outside its allowed values, or `confidence_reason` is empty | SC-003 |
| `client-ready` | `audience: client-ready` on any charter item | FR-036, SC-007 |
| `cited-source` | An `S-###` ID appears in any field of a charter item, or `origin: client-document` | FR-019 |
| `hypothesis-question` | A hypothesis's `question` isn't exactly one existing Q-ID | FR-015, SC-004 |
| `one-way-link` | H→Q isn't listed back in `Q.hypotheses`, or `Q.hypotheses` names an H whose `question` is a different Q | FR-015, SC-004 |
| `broken-link` | A link field names a Q/H/A ID that doesn't exist | FR-020 |
| `supersede-state` | An item with `status: superseded` is not listed in any other item's `supersedes`, or has no `change_reason` | FR-024 |
| `reject-state` | `status: rejected` with an empty `change_reason` | FR-026 |
| `model-use-mismatch` | `scope.md` and `engagement.md` disagree on `model_use` or `model_use_notes` | FR-005 |
| `real-name-leak` | A code name is in use, and the real client name appears in a charter file or the changelog | FR-037 |
| `approved-unconfirmed` | `charter_status: approved` while `model_use` is `unconfirmed` | FR-035 |

### 5.4 Gaps reported by `status` (not problems; `check` still passes)

Only items with status `proposed` or `active` count.

| Code | Gap | Source |
|---|---|---|
| `question-no-hypothesis` | A question with no proposed or active hypothesis | FR-031 |
| `hypothesis-no-reject` | A hypothesis whose `reject_if` is empty or missing | FR-031 |
| `hypothesis-no-confirm` | A hypothesis whose `confirm_if` is empty or missing | FR-015 |
| `assumption-no-basis` | An assumption whose `basis` is empty | FR-016 |
| `scope-section-empty` | A scope section still holding its seed guidance | FR-009, FR-039 |
| `no-stakeholders` / `no-lenses` | No table rows, or no bullets | FR-039 |
| `many-questions` | More than 10 proposed or active questions, more than half with no `priority` | edge case |

Objectives that no question covers, and deliverables with no date, need the text to be
read. The assistant finds those (FR-031).

### 5.3 Status transitions (applied only on the consultant's explicit instruction, FR-034)

~~~text
proposed --approve--> active
proposed --reject (reason, trigger)--> rejected
active   --reject (reason, trigger)--> rejected
active|proposed --new version approved--> superseded   (new version: proposed --approve--> active)
any      --audience--> client-ready                    NEVER by this skill
~~~

A `superseded` or `rejected` item is never edited again, except for the moved-link
removal in §7. A request to revise one is redirected to the current version or answered
with "this item was dropped" (edge case).

## 6. Revision (new version) — the pair of entries

| | Old item (`H-002`) | New item (`H-004`) |
|---|---|---|
| On creation | unchanged | `status: proposed`, `supersedes: ["H-002"]`, `change_reason`, `change_trigger`, same `question` as old unless the consultant says otherwise |
| On approval | `status: superseded`, `change_reason`/`change_trigger` copied from the new item | `status: active` |
| On rejection of the new version | unchanged | `status: rejected`, with `change_reason` and `change_trigger` |
| Changelog | one `supersede` event, subject `H-002 → H-004`, logged at approval | if the new version is rejected: one `reject` event, subject `H-004` |

For a new hypothesis, the question's `hypotheses` list gains the new ID at creation, so
links agree in both directions from the start. For a new question, its `hypotheses` list
starts empty, and hypotheses move only by `relink` (§7).

## 7. Link move (relink)

When a question version is approved, each active or proposed hypothesis of the old question
is moved only if the consultant says so:

- hypothesis `question`: old Q-ID → new Q-ID (its claim is unchanged)
- new question `hypotheses`: gains the H-ID
- old question `hypotheses`: loses the H-ID
- changelog: `relink`, subject `H-003: Q-002 → Q-005`

## 8. Stakeholder (`00-charter/stakeholders.md`)

A table row, not a numbered object.

| Column | Rule |
|---|---|
| Name | As the consultant gives it (stakeholders' own names are client data that stays in the engagement) |
| Role | Job or role in the engagement |
| Perspective | Their view of the problem. Sensitive notes (credibility, politics) are written only after the consultant confirms them (edge case). |
| Interview status | `not yet interviewed` (default) \| `scheduled` \| `interviewed` |

Rows are appended. An existing row is changed only on the consultant's instruction. A
`|` inside a cell is written as `\|`.

## 9. Lens and evaluation criterion (`00-charter/lenses.md`)

One bullet each, `- **<Name>**: <one-line description>`, under `## Lenses` or
`## Evaluation criteria`. Names are unique within a section, case-insensitively. The
starting lenses offered (FR-012) are Cost, Risk, Customer experience and Operating model.

## 10. Change event (`60-log/changelog.md`)

The format and the rules for when to log are in
[contracts/change-convention.md](contracts/change-convention.md). Summary: one line
`YYYY-MM-DD · <subject> · <event> · <reason> · <trigger>`, with an optional `> ` quoted
block underneath. Events: `supersede`, `correct`, `clarify`, `reject`, `scope-change`,
`relink`, `model-use`, `approve-charter`. Appended newest last. The first event replaces
"No changes yet."

## 11. Session record (in conversation only)

The skill keeps track, during the session, of:

- the IDs it created this session (these may be amended in place, R10)
- the topics covered and skipped (FR-009, FR-039)
- the suggestions offered, kept and discarded (count ≤ 5, FR-032)
- the objects flagged by `refs` (FR-029)

Nothing in the session record is written to disk, except as part of the end summary
shown to the consultant.
