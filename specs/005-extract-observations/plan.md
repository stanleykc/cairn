# Implementation Plan: Extract Observations Skill

**Branch**: `005-extract-observations` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-extract-observations/spec.md`

## Summary

Ship the third Cairn skill, `extract-observations`, stage 3 of the pipeline. It reads
ingested sources (`10-sources/extracted/S-###.md`) and proposes atomic, cited observations
(`O-###`) in `_inbox/`. Each one has one claim, the exact passage it came from, a locator,
the source's provenance, a capped confidence, and tags for the charter questions it bears
on. Steering (focus questions, exclusions, a stakeholder perspective) narrows the run.
Re-runs skip claims already recorded or rejected, and offer to tag existing observations
with new questions.

It follows the `ingest` pattern. **The assistant judges, the script checks and writes**
(R2):

- The assistant reads the source and drafts the claims, wording, passage, locator,
  questions and confidence. It puts them in a drafts JSON file.
- `scripts/observe.py` (standard library, Python 3.9+):
  - enforces the gates (policy, restricted, in-progress, retired sources);
  - checks every draft: the quote is word for word at the locator, in the content region
    and not in an excluded part; the confidence is under the cap; the question IDs exist;
    with a focus, the draft is on it; it isn't a duplicate or a rejected claim; the real
    client name doesn't leak;
  - computes the fields that are facts about the source: `origin`, `derived`, `speaker`,
    `passage_kind`, the confidence cap;
  - assigns the next free `O-###` and writes `_inbox/O-###.md`;
  - adds question tags on confirmation and logs a new `tag` event;
  - records progress for long sources.

Default breadth with no focus is **every factual claim**, untagged ones kept (R1,
clarified 2026-11-05).

Supporting changes:

- the observation template gains `speaker`, `passage_kind`, `translated` and a
  `## Claim` / `## Passage` body (R4);
- the shared change convention and changelog seed gain the `tag` event (R10);
- framework version 0.5.0 (R16).

## Technical Context

**Language/Version**: Markdown skill instructions in Claude Code Agent Skills format. The
helper script is Python **3.9+**, standard library only, run by the consultant's `python3`
(R3). The `cairn` package stays at Python 3.11+.

**Primary Dependencies**:
- Claude Code is the host assistant. It reads extracted markdown with its Read tool.
- No new Python dependencies. Poppler isn't used: the skill reads only extracted markdown.
- Dev: `pytest` and `PyYAML` (existing). Opt-in evaluation: the `claude` CLI.

**Storage**: Engagement markdown files:
- `_inbox/O-###.md` (new);
- `60-log/changelog.md` (`tag` events);
- `.cairn/work/extract-observations/` (drafts files and `progress.json`, R12).

The skill reads `engagement.md` (script only), `00-charter/questions.md`,
`10-sources/extracted/` and `30-observations/`. `10-sources/raw/` is never opened.

**Testing**: `pytest`:
- unit tests for every `observe.py` command and check code;
- an extended parity test for the copied parsing code;
- integration tests for bundling and refresh, golden observations and timing.

There's also an opt-in live-model evaluation under `tests/skill_eval`
(`CAIRN_SKILL_EVAL=1`) for US1–US4 and the edge cases (R17). Fixtures reuse
`tests/fixtures/ingest` and add golden observations. Everything is synthetic.

**Target Platform**: Claude Code on macOS and Linux consultant workstations.

**Project Type**: An agent skill plus a helper script, shipped as framework assets of the
existing `cairn` package.

**Performance Goals**:
- `status`, `prepare` and `verify` (all observations) finish in under 2 s on an
  engagement with 50 sources and 2,000 observations.
- `add` of a 40-draft file finishes in under 2 s.
- Session time is bounded by SC-006 (review under 10 minutes per typical source). That
  depends on the quality and number of observations, not on compute.

**Constraints**:
- No read of `raw/`, of restricted or content-removed sources, or of anything under
  `unconfirmed` (SC-003, FR-005/006).
- The assistant never reads `engagement.md` (002 R7).
- No network, no web or library tools (FR-009).
- Only `add` writes observation files. Only `tag` edits existing ones, and only their
  `questions` line.
- No links and no status other than `proposed` (FR-018/019, SC-008).
- About 40 proposed observations per session before a natural break (R12).
- `SKILL.md` stays at about 250 lines or fewer, with the detail in `reference/`.

**Scale/Scope**: 10–20 sources per engagement. Tens of observations per source, and a few
hundred per engagement. Documents up to about 200 pages, transcripts up to about 1,000
turns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / rule | How this plan complies | Status |
|---|---|---|
| I. Text-first | One skill folder: `SKILL.md`, reference files, one script. The script is used only where a deterministic check beats instructions: ID assignment, word-for-word quote checks, gates, caps (R2). Observations are plain markdown with front matter. Status lives in front matter. `progress.json` is a convenience, not a record (data-model §4). | Pass |
| II. Originals immutable | `raw/` is never opened by the skill or the script. Work is only on `10-sources/extracted/`. Tests hash `raw/` around every command. | Pass |
| III. Atomic, cited evidence | One claim per observation, enforced by the instructions and a reviewer check (SC-004). No ellipses, no joining passages (R5). Every observation cites `source` and a locator, and carries the passage, checked by the script (SC-001/002). Context and Description are never cited (`quote-outside-content`). | Pass |
| IV. Provenance and inference | `origin` is copied from the source. `llm-inference` sources are refused, so the skill writes nothing inferred. Confidence is capped, with a reason (§1.3). `derived` is computed from the callouts (R6). | Pass |
| V. Stable IDs, link by ID | The next free `O-###` comes from scanning the whole engagement (R8). Never reused. Question tags are IDs only. One observation per file (no per-source grouping). | Pass |
| VI. Never delete, supersede | Nothing is deleted or overwritten. `tag` adds IDs only and is logged with a date (`tag` event, R10). Rejected observations are kept and block re-proposal (R9). | Pass |
| VII. Agents propose (NON-NEGOTIABLE) | Written `proposed` and `internal` to `_inbox/` from `_templates/observation.md`. No status changes, no links, no `client-ready`. Tags are added only after the consultant confirms. | Pass |
| VIII. Confidentiality (NON-NEGOTIABLE) | Policy and restriction gates are enforced twice: by the instructions, and by the script (`status`, `prepare`, `add`; R13). No network. Code-name leak check on titles and claims (R14). Fixtures are synthetic, and the trial engagement stays local. | Pass |
| Canonical layout | No folders added. Writes go to `_inbox/`, `60-log/changelog.md` and `.cairn/work/` (internal). | Pass |
| Skill Contract 1–6 | (1) `raw/` untouched. (2) Every observation is cited with a locator. (3) Nothing inferred is written. (4) `proposed`, to `_inbox/`, from the template. (5) Next free ID, links by ID. (6) Never `client-ready`. | Pass |
| Skill-specific: extract-observations | Atomic, no interpretation: the instructions have worked examples, contiguous-quote checks and attribution warnings, plus a reviewer-scored SC-004. | Pass |
| Workflow: spec-driven, minimal | The spec is clarified (R1). Data-model changes are limited to what FR-012/013/023 need. The template, every copy of the change convention, the changelog seed and the 001/002 docs are updated together (R15). | Pass |
| Workflow: validation on known outcomes | SC-005/006 are validated on the local anonymized trial engagement (quickstart §8). Nothing from it is committed. | Pass |
| Review gate | The PR checklist runs `observe.py verify` on golden observations (citations, provenance, `proposed`, ID-only links). | Pass |

**Post-design re-check (after Phase 1)**: Still passes. The design adds:
- no folders and no dependencies;
- one new changelog event (`tag`);
- three additive template fields and a body change.

The template change is additive. Existing engagements have no observations written by a
skill yet. Hand-written ones without the new fields still pass `verify`: the new fields
default to empty, and the passage check applies only when `## Passage` is present. Hand
observations are flagged `passage-missing` as a warning, not an error.

## Project Structure

### Documentation (this feature)

```text
specs/005-extract-observations/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R18
├── data-model.md        # Phase 1: observation fields, drafts, locators, progress, check codes, tag event
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── extract-observations-skill.md   # invocation, session flow, never-do list, end summary
│   ├── observe-script.md               # observe.py commands, JSON output, exit codes, file access
│   └── observation-file.md             # the observation format and guarantees to later skills
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/cairn/
├── __init__.py                                   # __version__ 0.4.0 → 0.5.0 (R16)
└── assets/
    ├── skills/
    │   ├── charter/reference/change-convention.md    # + tag event (R10)
    │   ├── ingest/reference/change-convention.md     # + tag event (byte-identical)
    │   └── extract-observations/                     # NEW
    │       ├── SKILL.md
    │       ├── reference/
    │       │   ├── writing-observations.md           # atomicity, attribution, examples per material
    │       │   └── change-convention.md              # byte-identical copy
    │       └── scripts/
    │           └── observe.py                        # stdlib, Python 3.9+
    ├── templates/observation.md                  # speaker, passage_kind, translated, Claim/Passage body (R4)
    └── seed/60-log/changelog.md                  # event list + tag (R10)

specs/001-engagement-init/data-model.md           # observation template row updated
specs/002-charter-skill/contracts/change-convention.md   # mirrors the updated convention

tests/
├── unit/
│   ├── test_observe_script.py                    # gates, numbering, quote matching per format, computed fields, caps, steering, duplicates, tag, verify, raw/ untouched
│   └── test_ingest_parity.py                     # EXTENDED: observe.py parsing and unit splitting match ingest.py
├── integration/
│   ├── test_observe_bundle.py                    # init ships 3 skills; refresh 0.4.0 → 0.5.0; settings rule; template fields; convention copies identical
│   ├── test_observe_golden.py                    # verify on golden observations, expected codes on broken ones
│   ├── test_observe_perf.py                      # timing goals
│   └── test_init.py                              # UPDATED: bundled skill count 3, README lists the skill
├── fixtures/observe/
│   ├── golden/                                   # synthetic engagement: sources + expected observations
│   └── README.md                                 # includes the SC-004 reviewer rubric
└── skill_eval/scenarios/extract-observations/*.yaml   # NEW: US1–US4 and edge cases
```

**Structure Decision**: No new package code. The feature lives in framework assets, which
`init` and `refresh` already distribute, plus tests. The script is self-contained in the
skill folder, so each engagement uses the copy pinned to its own framework version. Unit
tests import it by path. Integration tests run it as a subprocess against fixture
engagements.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| A helper script (about 900 lines expected) with copied parsing and unit-splitting code from `ingest.py` | SC-001/002 need automated checks of every field and every quote. ID assignment must be deterministic (R2, R3). | Instructions only can't guarantee 100%. A cross-skill import breaks when skills are refreshed separately. |
| A third copy of the shared parsing code, where 003 R3 deferred a shared module "until a third skill" | Extracting a shared module now means refactoring two shipped scripts inside this feature (R3) | The parity test is extended to all three scripts. **Follow-up:** a separate feature extracts a byte-identical `cairn_common.py` into each skill, with an identity test. |
| A new changelog event (`tag`) and a fourth copy of the change convention | FR-023 requires logging tag additions. No existing event means "a question tag was added" (R10). | `relink` means a link moved between versions. Reusing it would mislead `what-changed`. |
| A drafts file in `.cairn/work/` | Lets the script check a batch before anything lands in `_inbox/` (R2) | Writing files and verifying afterwards puts wrong files in front of the consultant. |

## Decisions Confirmed by the Project Owner (2026-11-05)

1. With no focus, extract every factual claim. Keep untagged claims and list them
   separately (R1).

## Open Points for Review

None block the tasks phase. They're worth confirming at plan review:

- The three-way copy of the parsing code, rather than extracting the shared module now
  (R3, Complexity Tracking).
- The new `tag` changelog event (R10).
- Stopping at about 40 observations per session (R12).
