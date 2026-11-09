# Contract delta: `observe.py`

Amends `specs/005-extract-observations/contracts/observe-script.md`. Commands, exit codes
and outputs not listed here are unchanged.

## `status [S-ID …]`

Three keys are added to the output:

```json
{
  "charter_status": "approved",
  "usable_questions": 4,
  "sources": [
    {"id": "S-001", "…": "…",
     "progress": {"state": "done", "questions": ["Q-001", "Q-002", "Q-003", "Q-004"]},
     "new_questions": ["Q-005"]}
  ]
}
```

- `charter_status`: the `charter_status` field from `00-charter/scope.md` (`draft` or
  `approved`), or `""` when it is missing.
- `usable_questions`: the count of questions with status `active` or `proposed`.
- `new_questions`: the usable question IDs that are missing from `progress.questions`. It
  is `[]` when the source isn't done, or when the progress entry has no `questions`.

`status` never refuses because there are no questions.

## `prepare S-ID [--confirmed]`

New refusal, checked after the policy gate and before the source gate:

| Exit | Error | Payload |
|---|---|---|
| 6 | `no-questions` | `{"error": "no-questions", "message": "The charter has no active or proposed questions. Run /charter first."}` |

A `done` source is not refused and needs no `--confirmed` (FR-013); this is unchanged
from 005 and now covered by a test.

One key is added to the output:

```json
{"source": {"…": "…"}, "units": ["…"], "density_limit": 12}
```

- `density_limit`: `max(1, floor(turns / 10))` when the units are transcript turns,
  `max(1, pages)` when they are pages, otherwise `null`. Counted over the whole source,
  before steering exclusions (research R11).

## `add DRAFTS.json [--dry-run] [--confirmed]`

- Exits 6 with `no-questions` (same payload as `prepare`) before checking any draft.
- `relevance` is required. The checks per draft, in order, are added after
  `check_questions`:
  1. `questions` empty → refuse `untagged`.
  2. `relevance` missing or blank → refuse `relevance-missing`.
  3. `relevance` with a line break, or longer than 240 characters → refuse `bad-value`.
  4. Any tagged Q-ID that doesn't appear in `relevance` → refuse `relevance-unlinked`
     (the detail names the missing IDs).
  5. Normalised `relevance` (lower case, collapsed whitespace, without Q-ID prefixes) equal
     to the normalised claim, or contained in it → refuse `relevance-restates-claim`.
- `check_questions`: a tag to a `superseded` or `rejected` question is now a refusal,
  `question-retired`, instead of a warning.
- The written file carries `relevance` as given, rendered as a quoted one-line string.

## `progress S-ID --done [--steering-from DRAFTS.json]`

Also stores `questions`: the usable question IDs at that moment, sorted. `--stopped-at` is
unchanged.

## `verify [O-ID …]`

Unchanged for stored observations that have no `relevance` field. When `relevance` is
present, `verify` checks it is a one-line string. It does not re-check linkage, so that a
later `tag` (which adds a question without a reason) never makes `verify` fail.

## `tag O-ID Q-ID …`

Unchanged. It now refuses `question-retired` for a superseded or rejected question, which
matches `add`.
