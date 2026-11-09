# Data Model: Charter-Relevant Observations

Changes to the 005 data model (`specs/005-extract-observations/data-model.md`). Everything
not listed here is unchanged.

## 1. Observation (`_inbox/O-###.md`): changed

New front-matter field, placed after `questions`:

| Field | Type | Set by | Rule |
|---|---|---|---|
| `relevance` | string, one line, ≤ 240 chars | assistant (draft) | Required for new observations. Names every tagged Q-ID: `"Q-001: <how it bears>; Q-003: <how it bears>"`. Must not repeat the claim. |

Changed rules:

| Field | 005 | 006 |
|---|---|---|
| `questions` | may be `[]` (untagged) | at least one ID, each with status `active` or `proposed` when written |
| `relevance` | absent | required on new observations; optional on stored ones (no migration) |

Template line (`src/cairn/assets/templates/observation.md`):

```yaml
questions: []             # Q-IDs; at least one
relevance: ""             # one line: how the claim bears on each tagged question, "Q-###: …"
```

## 2. Draft (in `drafts-<S-ID>-<n>.json`): changed

The draft now requires `relevance` (added to `DRAFT_REQUIRED`), and `questions` must not be
empty.

```json
{"source": "S-001", "locator": "T42", "quote": "…", "claim": "…", "title": "…",
 "questions": ["Q-001"],
 "relevance": "Q-001: names a manual re-keying step in order to cash",
 "confidence": "medium", "confidence_reason": "…", "translated": false}
```

## 3. Usable question (derived, not stored)

A question in `00-charter/questions.md` whose `status` is `active` or `proposed`. Questions
that are `superseded` or `rejected` can't be tagged. With zero usable questions, `prepare`
and `add` refuse (`no-questions`).

## 4. Progress (`.cairn/work/extract-observations/progress.json`): changed

A `done` entry also records the usable questions at the time of the pass:

```json
{"S-001": {"state": "done", "steering": {…}, "questions": ["Q-001", "Q-002", "Q-003", "Q-004"],
           "updated": "2026-11-09"}}
```

Entries written before this change have no `questions`. `status` then reports
`new_questions: []`, because there is no baseline. The skill does not guess.

## 5. Passed-over material (session only, never stored)

Held by the assistant during the session and printed in the summary. No file, log or
work-file entry (FR-010).

- **Passed-over topic**: `{label, locator_range}` for each distinct off-charter topic
  longer than a passing remark (about 3 or more turns, or a paragraph or more). Optional
  flag `may_matter` → printed with "consider /charter".
- **Brief remarks**: a single count of shorter asides, printed as `other brief remarks: N`.
  Not labelled.

## 5a. Density limit (derived, not stored)

Returned by `prepare` as `density_limit` (research R11):

| Source units | `density_limit` |
|---|---|
| turns (`T#` units) | `max(1, floor(turns / 10))` |
| pages (`p. #` units) | `max(1, pages)` |
| other | `null` (no flag) |

The skill flags a source in the summary when the observations `add` wrote for it in this run
exceed `density_limit`. It is never a refusal and never drops a draft (FR-016).

## 6. Refusal and warning codes

| Code | Kind | When |
|---|---|---|
| `untagged` | refusal | `questions` is empty |
| `relevance-missing` | refusal | `relevance` missing or blank |
| `relevance-unlinked` | refusal | a tagged Q-ID isn't named in `relevance` |
| `relevance-restates-claim` | refusal | normalised `relevance` equals, or is contained in, the normalised claim |
| `question-retired` | refusal (was a warning) | a tag names a `superseded` or `rejected` question |
| `no-questions` | exit 6 on `prepare` and `add` | no usable questions in the charter |

No code is added for density: it is a summary line, not a refusal or warning.

`question-retired` leaves `WARNING_CODES`, so it can no longer be accepted with
`accept_warnings`.
