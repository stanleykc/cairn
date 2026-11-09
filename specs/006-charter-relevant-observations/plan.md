# Implementation Plan: Charter-Relevant Observations

**Branch**: `006-charter-relevant-observations` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-charter-relevant-observations/spec.md`

## Summary

`extract-observations` (005) proposes every factual claim in a source. In a trial, it turned
one meeting transcript into 157 observations, many with only a loose link to the charter.
This change makes **relevance to the charter** a condition for writing an observation.

It keeps 005's split: **the assistant judges, the script checks** (research R1).

- **The assistant** reads the charter (questions, hypotheses, assumptions, scope). It
  applies a written relevance test to each candidate claim, and drafts only relevant claims.
  Each draft gets a new one-line `relevance` reason that names every tagged question.
  Off-charter material is listed in the summary under "Passed over" and nowhere else:
  every topic of about 3 or more turns (or a paragraph) by label and locator range, and
  shorter asides as one counted line. The summary also flags a source whose count exceeds
  the density limit and suggests a narrower focus; nothing is capped.
- **`observe.py`** enforces what can be checked mechanically. It refuses drafts that are
  untagged, have no `relevance`, have a `relevance` that doesn't name every tagged question
  or that restates the claim, or are tagged to a retired question. `prepare` and `add` stop
  when the charter has no usable questions. `prepare` returns `density_limit` (one per 10
  turns, or one per page). `status` reports the charter's status and which questions a
  finished source predates. A plain re-run of a finished source re-checks it against every
  current question without asking, and the existing duplicate checks keep it to new claims
  (US3).

No migration. 005-era observations stay valid. The new template field reaches existing
engagements through `cairn refresh`.

## Technical Context

**Language/Version**: Python 3.9+ (standard library only in the skill script); the dev
machine runs 3.14

**Primary Dependencies**: none at runtime; pytest and PyYAML for tests

**Storage**: plain markdown files with YAML front matter in the engagement folder;
`.cairn/work/extract-observations/progress.json` for progress

**Testing**: pytest (unit, integration, golden fixtures); skill evals behind
`CAIRN_SKILL_EVAL=1`

**Target Platform**: Claude Code skill running in a local engagement folder (macOS or Linux)

**Project Type**: CLI package (`cairn`) that ships skills as bundled assets

**Performance Goals**: unchanged from 005 (`test_observe_perf.py`); the new checks are O(1)
per draft

**Constraints**: constitution I (scripts only for deterministic checks), III (atomic claims,
no interpretation in the claim), VII (agents propose), VIII (synthetic fixtures only)

**Scale/Scope**: one skill (SKILL.md and two reference files), one script (about 7 functions
touched), one template line, test updates; no new commands

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Text-first | Still plain files. The script gains checks only where they are deterministic (tags present, IDs named, the density threshold from unit counts); the relevance judgment and the "passing remark" size rule stay in instructions. | Pass |
| II. Originals immutable | No change; the skill reads only `10-sources/extracted/`. | Pass |
| III. Atomic, cited evidence | The claim stays one claim with no interpretation. The relevance reason is the skill's judgment, held in its own field (like `confidence_reason`), never in the claim. The constitution's skill rule for `extract-observations` (atomic, no interpretation) is preserved. | Pass |
| IV. Provenance | `origin` and `confidence` are unchanged. `relevance` is labelled as the skill's reasoning in the template comment. | Pass |
| V. Stable IDs | No change to ID assignment. Passed-over material gets no IDs. | Pass |
| VI. Never delete | Existing observations are not changed or backfilled. `tag` stays logged. | Pass |
| VII. Agents propose | Output is still `proposed` in `_inbox/`. The consultant sees what was passed over and decides whether to add a question. The skill never creates questions. A plain re-run of a finished source proposes only new claims; retagging still asks first. The density flag suggests a narrower focus but never drops a draft. | Pass |
| VIII. Confidentiality | The trial engagement is cited only anonymously and by counts. All fixtures and examples are synthetic. Passed-over material isn't persisted. | Pass |
| Skill Contract 1–6 | Unchanged. Templates are still used, so the new field comes from `_templates/observation.md`. | Pass |
| Gate 1 (rebuild key findings) | Risk: fewer observations could lower recall. Mitigation: the relevance test includes hypotheses and assumptions, "unsure" is reported under "Passed over", and re-runs for new questions (R6). Measured by SC-002 and SC-006. | Pass, risk tracked |

**Post-design re-check** (after the 2026-11-09 clarifications): the design adds one field,
one progress key, three `status` keys and one `prepare` key, all plain text. The
passed-over list and the density flag live only in the summary, so FR-010 holds. No
violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-charter-relevant-observations/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── observe-script.md              # delta to 005 contract
│   ├── extract-observations-skill.md  # delta to 005 contract
│   └── observation-file.md            # delta to 005 contract
├── checklists/requirements.md
└── tasks.md                           # /speckit-tasks
```

### Source Code (repository root)

```text
src/cairn/assets/
├── templates/observation.md                       # + relevance line; questions comment
└── skills/extract-observations/
    ├── SKILL.md                                   # description, Never #9, Steps 1–4, 6
    ├── reference/writing-observations.md          # + Relevance section; rewrite Tagging; granularity
    └── scripts/observe.py                         # SKILL_FIELDS, DRAFT_REQUIRED, check_relevance,
                                                   # check_questions, no-questions gate, status, progress,
                                                   # prepare density_limit, verify
src/cairn/__init__.py                              # version bump (template change)

specs/
├── 001-engagement-init/data-model.md              # observation field list + relevance
└── 005-extract-observations/                      # amend spec R1 note, contracts, data-model to point at 006

tests/
├── unit/test_observe_script.py                    # new refusals, status keys, progress, verify
├── integration/test_observe_golden.py             # expected files carry relevance
├── integration/test_observe_bundle.py             # description, NEW_FIELDS + relevance
├── integration/test_init.py                       # template field present
├── fixtures/observe/golden/us1–us4/               # drafts.json and expected/O-*.md gain relevance
├── fixtures/observe/golden/us6-relevance/         # new synthetic transcript + answer key (long topics + brief asides)
├── fixtures/observe/golden/us8-density/           # new short, dense, all-relevant transcript
└── skill_eval/scenarios/extract-observations/
    ├── us2-no-questions.yaml                      # expect stop, never_read S-001
    ├── us6-relevance.yaml                         # new: relevance, Passed over, brief-remarks count
    ├── us7-new-question-rerun.yaml                # new: plain re-run of a done source, no confirmation
    └── us8-density.yaml                           # new: density flag, nothing dropped
```

**Structure Decision**: single package. All changes are inside the existing
`extract-observations` skill bundle, its template, its tests and fixtures, and the 005 and
001 design docs that describe the observation file.

## Implementation Order

1. **Template and field lists**: add `relevance` to `observation.md`, `SKILL_FIELDS` and
   `DRAFT_REQUIRED`, and bump the version. Golden expected files fail until step 4.
2. **Script checks** (contracts/observe-script.md):
   - `check_relevance`;
   - `question-retired` becomes a refusal;
   - the `no-questions` gate in `prepare` and `add`;
   - the `status` keys;
   - `progress --done` records `questions`;
   - `prepare` returns `density_limit`, and still accepts a `done` source without
     `--confirmed`;
   - `verify` tolerates a missing `relevance`.

   Unit tests are written first, for each item.
3. **Skill text**: SKILL.md and writing-observations.md, per
   contracts/extract-observations-skill.md and research R6–R9 and R11 (plain re-run,
   passed-over size rule, density line).
4. **Fixtures**: add `relevance` to the us1–us4 drafts and expected files; build the
   synthetic `us6-relevance` transcript and answer key, and the `us8-density` transcript.
5. **Skill evals**: update `us2-no-questions`; add `us6-relevance`,
   `us7-new-question-rerun` and `us8-density`.
6. **Docs**: amend the 005 spec, data model and contracts, and the 001 data model, with
   pointers to 006.
7. **Manual check**: run the quickstart §3 on the trial engagement (consultant).

## Complexity Tracking

No violations.
