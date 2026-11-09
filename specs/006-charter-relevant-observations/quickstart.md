# Quickstart: validating charter-relevant observations

How to check that this feature works. The details are in [data-model.md](data-model.md) and
[contracts/](contracts/).

## Prerequisites

- The repository is installed for development: `python3 -m pip install -e '.[dev]'`.
- To run the skill evals: Claude Code is available, with `CAIRN_SKILL_EVAL=1`.

## 1. Deterministic checks

```bash
python3 -m pytest tests/unit/test_observe_script.py tests/integration/test_observe_golden.py \
  tests/integration/test_observe_bundle.py tests/integration/test_init.py -q
```

Expected:

- Drafts with `questions: []`, a missing `relevance`, or a `relevance` that doesn't name a
  tagged Q-ID are refused, with `untagged`, `relevance-missing` or `relevance-unlinked`.
- A tag to a rejected question is refused with `question-retired`.
- `prepare` and `add` exit 6 with `no-questions` on a charter with no usable questions.
  `status` still answers, with `usable_questions: 0`.
- `progress --done` stores `questions`. Adding a question later makes it appear in that
  source's `new_questions`. `prepare` on that `done` source succeeds without `--confirmed`.
- `prepare` returns `density_limit`: 12 for a 120-turn transcript, the page count for a
  paged document, 1 for a 5-turn transcript, and `null` for an unpaged document.
- `verify` passes on the older observations in `golden/us4`, which have no `relevance`.
- Freshly initialised engagements have `relevance` in `_templates/observation.md`. An
  engagement with the old template gets `template-outdated` until `cairn refresh`.

## 2. Skill evals (relevance judgment)

```bash
CAIRN_SKILL_EVAL=1 python3 -m pytest tests/skill_eval -k extract-observations -q
```

Expected:

- `us6-relevance` (synthetic transcript, seeded answer key):
  - every new observation matches `^relevance: ".+"` and none matches `^questions: \[\]$`
    (SC-001);
  - no seeded off-charter topic appears in a new observation, and at least 90% of the
    seeded relevant claims do (SC-002);
  - the transcript contains `Passed over`, a label keyword for each seeded topic of 3 or
    more turns, and `other brief remarks` (FR-009).
- `us2-no-questions`: no observations, `/charter` suggested, the source never read.
- `us7-new-question-rerun`: after a question is added, a plain `/extract-observations S-001`
  on the `done` source asks no confirmation, proposes the seeded claims for the new
  question, and duplicates nothing (FR-013, SC-006).
- `us8-density`: the summary flags the source and suggests a narrower focus; every seeded
  relevant claim is still proposed (FR-016).
- All other 005 scenarios still pass, with `relevance` present on their outputs.

## 3. Consultant's manual check (trial engagement; never copied into the repository)

1. In the trial engagement, run `cairn refresh`, and move the 005-era `_inbox/` files
   aside (or reject them in triage).
2. Run `/extract-observations S-001`.
3. Check:
   - the count is at least 60% below 157 (SC-003);
   - the consultant agrees with the relevance reason on at least 18 of 20 sampled
     observations (SC-004);
   - triage takes under 20 minutes (SC-005);
   - "Passed over" lists the introductions, anecdotes and tool remarks, and counts the
     brief asides on one line;
   - if the count is still above one per 10 turns, the summary shows the "High density"
     line.
