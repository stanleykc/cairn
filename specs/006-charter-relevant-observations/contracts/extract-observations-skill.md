# Contract delta: `extract-observations` skill

Amends `specs/005-extract-observations/contracts/extract-observations-skill.md`. Sections not
mentioned are unchanged.

## Front matter

```yaml
description: "Pull atomic, cited observations that bear on the charter's questions from ingested sources into _inbox/. Use after ingest, or when a new question needs evidence from sources already ingested."
```

The argument hint is unchanged.

## Never (adds one rule)

9. Never propose a claim that bears on no usable charter question. Never tag a question
   without saying, in `relevance`, how the claim bears on it.

## Step 1: Status

- Note `charter_status`, `usable_questions`, and each source's `new_questions`.
- With no arguments, also list sources that are `done` but have `new_questions`, for
  example: "S-001 — processed before Q-005; run `/extract-observations S-001 for Q-005`".

## Step 2: Charter

- `usable_questions: 0` → say the charter has no questions to judge relevance against,
  suggest `/charter`, and stop. Read no source and write nothing. (This replaces 005's
  "continue untagged" path.)
- Otherwise, Read `00-charter/questions.md`, `hypotheses.md`, `assumptions.md` and
  `scope.md`. Keep for the session:
  - each usable question;
  - its hypotheses' `confirm_if` and `reject_if`;
  - the assumptions that list it;
  - the in-scope and out-of-scope lists.
- `charter_status: draft` → carry on, and note it for the summary.

## Step 3: Steering

- No focus → every **charter-relevant** claim (not every factual claim).
- A focus narrows the run to the named questions, as before.
- A source in the arguments that is `done` with `new_questions`, and has no focus: suggest
  focusing on the new questions, and ask once.

## Step 4: Each source

For each candidate claim, apply the relevance test from `reference/writing-observations.md`
§ Relevance before drafting it:

- Relevant → draft it with `questions` and `relevance`.
- Off-charter, or unsure → don't draft it. Note its topic and locator for "Passed over".

Split a passage only when each part is relevant on its own. Record a repeated point once.

## Step 6: Summary

- Remove the `Untagged:` group.
- Add a line, shown only when the charter is unapproved:
  `Charter not yet approved: questions are proposed`.
- Add this section, shown when anything was passed over:

```text
Passed over as off-charter (no observations written):
  introductions · T1–T12
  a past project at another company · T140–T171
  office tools · T88–T93
  May matter, fits no current question: a planned warehouse move · T201–T206 → consider /charter
```

- Steering line: `none (every charter-relevant claim)` replaces
  `none (every factual claim)`.
