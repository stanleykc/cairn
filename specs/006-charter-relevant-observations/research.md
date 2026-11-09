# Research: Charter-Relevant Observations

Decisions for changing `extract-observations` (005) so that it proposes only claims that
bear on the charter. Each entry follows the 005 pattern: the assistant judges, and the
script checks what can be checked mechanically.

## R1. Where the relevance judgment lives

- **Decision**: The assistant judges relevance. The script enforces the structural signs of
  that judgment: every draft must carry at least one usable question tag, plus a relevance
  reason that names each tagged question.
- **Rationale**: Whether a claim is evidence for a question is a judgment about meaning. A
  script can't make it reliably (constitution I: scripts only where a deterministic check
  beats instructions). The script can still make the judgment explicit and checkable. A
  draft with no tag, or with a tag that has no stated reason, is refused before it reaches
  `_inbox/`. That closes both failure modes from the trial: untagged claims, and claims with
  a loose tag and no reason.
- **Alternatives considered**: a keyword or similarity score between the claim and the
  question text (brittle, misses paraphrase, and gives false confidence); a second model
  pass to grade relevance (adds cost and a second judge without a clear gain; can be
  revisited if SC-004 fails).

## R2. Recording the reason: a new `relevance` field

- **Decision**: Add `relevance: ""` to the observation template and to `SKILL_FIELDS`. It
  holds one line, in the form `Q-001: <how it bears>; Q-003: <how it bears>`. Drafts must
  supply it. `add` refuses a draft when:
  - the reason is missing (`relevance-missing`);
  - a tagged question isn't named in it (`relevance-unlinked`);
  - it is just the claim repeated (`relevance-restates-claim`);
  - it is longer than 240 characters or spans several lines (`bad-value`).
- **Rationale**: FR-004 keeps the claim free of interpretation (005 FR-010). The reason is
  interpretation, so it gets its own field, next to `confidence_reason`, which has the same
  shape. Naming each tagged Q-ID makes FR-005 (no loose tags) checkable: every tag must be
  justified in words.
- **Alternatives considered**: a body section `## Relevance` (harder for the script to
  check, and buried below the passage); one reason per tag as a mapping (heavier YAML for a
  small gain; the `Q-ID:` prefix gives the same check).

## R3. Existing engagements and existing observations

- **Decision**: `template_keys` already refuses with `template-outdated` when the
  engagement's `_templates/observation.md` lacks a skill field. Adding `relevance` to
  `SKILL_FIELDS` makes older engagements get that message, and `cairn refresh` fixes it.
  `relevance` is **not** added to `STORED_REQUIRED`, so `verify` keeps accepting
  observations written before this change (spec: no migration).
- **Rationale**: This reuses the existing upgrade path, and leaves 005-era observations
  for the consultant to handle in triage.
- **Alternatives considered**: backfilling `relevance` on existing observations (it would
  change objects without the consultant, and it can't be done honestly for loosely tagged
  ones).

## R4. Retired questions and no usable questions

- **Decision**: Usable questions are those whose status is `active` or `proposed`.
  - `add` now **refuses** a tag to a `superseded` or `rejected` question
    (`question-retired`, previously a warning).
  - `prepare` and `add` exit 6 with `no-questions` when the charter has no usable
    questions. `status` still answers, and reports `usable_questions: 0` so the skill can
    stop at Step 2 before reading anything (FR-011).
- **Rationale**: Relevance to a retired question is not relevance to the charter. Putting
  the stop in the script as well as in the instructions makes FR-011 hold even if the
  assistant skips Step 2.
- **Alternatives considered**: keeping the warning (it would let loose tags back in);
  letting the skill continue without questions (this was 005's behaviour, and it is what
  produced the untagged flood).

## R5. Unapproved charter

- **Decision**: `status` reports `charter_status` (from `00-charter/scope.md`,
  `draft | approved`). The skill extracts against proposed questions and adds a
  "Charter not yet approved" line to the summary (FR-012).
- **Rationale**: Early in an engagement the charter is often still a draft, and blocking
  extraction would stall the pipeline. Questions stay `proposed` until the consultant
  approves them, and observations do too, so nothing is promoted silently.

## R6. Re-running a finished source for a new question

- **Decision**: `progress S-ID --done` also records `questions`: the usable question IDs at
  the time of the pass. `status` adds `new_questions` to each source: the usable questions
  not in that list. Nothing in `prepare` blocks a `done` source (true already). The skill
  instructions say: a source marked done with `new_questions` can be re-run with
  `for <new Q>`. Without a focus, the skill suggests that run instead of a full re-pass.
- **Rationale**: This gives US3 a precise prompt ("S-001 was processed before Q-005
  existed"), with no new state machine. The existing duplicate and rejected-claim checks
  (005 FR-022) and the retag offer (005 FR-023) already cover the rest.
- **Alternatives considered**: storing passed-over passages for later re-use. FR-010 forbids
  it, and the source itself is the record.

## R7. Passed-over material

- **Decision**: The skill keeps passed-over topics only in its working memory for the
  session, and reports them in the summary's "Passed over" section: a short label and a
  locator or range per topic. It adds one "may matter → `/charter`" line where relevant.
  The script records nothing about them.
- **Rationale**: FR-009 and FR-010. The consultant sees what was left out, and no file or log
  grows from off-charter material.
- **Alternatives considered**: a `passed_over` list in the drafts file (it would persist in
  `.cairn/work/`, against FR-010); a per-source report file (same issue).

## R8. Granularity (FR-008)

- **Decision**: Handled by instructions and examples in `reference/writing-observations.md`.
  Split a passage only when each part is relevant on its own. Record a repeated point once,
  citing its clearest occurrence. Background detail inside a relevant passage stays in the
  quote and is not given its own observation. The script doesn't enforce a count.
- **Rationale**: A numeric cap would cut relevant evidence from dense sources. Relevance plus
  the "each part relevant on its own" rule cuts the fragments seen in the trial (for example
  five observations about one anecdote).
- **Alternatives considered**: a per-unit or per-source cap (arbitrary, and it hurts dense
  documents); a `same-unit` warning (noisy for tables, where several rows are rightly
  separate observations).

## R9. Relevance guidance content

- **Decision**: Add a "Relevance" section to `reference/writing-observations.md` with:
  - the test: "Would this help answer a question, or confirm or reject a hypothesis or an
    assumption?";
  - how to use hypotheses' `confirm_if` and `reject_if`, assumptions' `questions`, and the
    scope's in-scope and out-of-scope lists;
  - a synthetic table of relevant and off-charter claims (introductions, past employers,
    anecdotes, office tools, scheduling, wishes not covered by a question);
  - the "unsure → leave out and list under Passed over" rule;
  - relevance-reason examples.

  Rewrite "Tagging and steering" to remove "keep every factual claim" and "Untagged".
- **Rationale**: FR-014. The skill reads the four charter files (`questions.md`,
  `hypotheses.md`, `assumptions.md`, `scope.md`) in Step 2. They are small, and they are
  already within the skill's read permissions.

## R10. Testing

- **Decision**:
  - **Unit tests** (`tests/unit/test_observe_script.py`): the new refusals (`untagged`,
    `relevance-missing`, `relevance-unlinked`, `relevance-restates-claim`,
    `question-retired`, `no-questions`); `status` fields (`usable_questions`,
    `charter_status`, `new_questions`); `progress --done` recording questions; `verify`
    accepting observations without `relevance`.
  - **Golden fixtures**: add `relevance` to every expected `O-###.md` and to the drafts
    files.
  - **New synthetic fixture** `golden/us6-relevance`: a meeting transcript with seeded
    relevant claims and seeded off-charter topics, plus an answer key.
  - **Skill-eval scenarios**: a new `us6-relevance.yaml`, using the existing `per_source`
    `all_match` and `none_match` and `none_new_match` keys; `us2-no-questions` updated to
    expect a stop; a new `us7-new-question-rerun.yaml`.
  - **Bundle test**: the 005 contracts path stays. The contract text that changes is in
    this feature's contracts, and the 005 contracts are amended to match.
- **Rationale**: Mechanical rules are tested deterministically. Relevance itself is tested
  through skill evals against an answer key (SC-001, SC-002, SC-006). SC-003 to SC-005 are
  the consultant's manual check on the trial engagement, which never enters the repository.
