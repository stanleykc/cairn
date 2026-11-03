# Implementation Plan: Charter Skill

**Branch**: `002-charter-skill` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-charter-skill/spec.md`

## Summary

Ship the first Cairn skill, `charter`. It interviews the consultant to frame the
engagement (scope, key questions, hypotheses, assumptions, stakeholders, lenses), settles
the model-use policy, and records approvals and revisions without ever reading a client
document.

The skill is a Claude Code skill folder bundled in `src/cairn/assets/skills/charter/`, so
`cairn init` and `cairn refresh` deliver it with no command changes. It has three parts:

- `SKILL.md` holds the session flow and the hard rules.
- `reference/` holds the interview, revision and change-convention guidance, loaded when
  the session needs it.
- `scripts/charter.py` is a standard-library helper (Python 3.9+). It finds the engagement,
  reports items, next free IDs, problems and gaps as JSON, lists objects that link to an
  ID, and writes the model-use policy to both files.

The assistant writes entries from the engagement's templates and runs `check` after each
write. Supporting changes:

- two new standard fields on every template (`change_reason`, `change_trigger`);
- two new hypothesis fields (`confirm_if`, `reject_if`);
- a `model_use_notes` field;
- approval fields and a Constraints section in `scope.md`;
- the changelog seed rewritten to a shared change convention, which `record-change` will
  reuse (FR-030);
- a framework version bump to 0.2.0.

## Technical Context

**Language/Version**: Markdown skill instructions in Claude Code Agent Skills format. The
helper script is Python **3.9+**, standard library only, because it runs under the
consultant's `python3` and not the `cairn` virtual environment (research R3). The `cairn`
package stays at Python 3.11+.

**Primary Dependencies**: No new runtime dependencies. Claude Code is the host assistant.
Dev: `pytest`, `PyYAML` (existing). Opt-in evaluation: the `claude` CLI.

**Storage**: Engagement markdown files: `00-charter/*.md`, `60-log/changelog.md`, and two
fields of `engagement.md`.

**Testing**: `pytest`. Unit tests for the script, integration tests for bundling and
refresh, and golden synthetic charters checked with `charter.py check`. An opt-in live-model
skill evaluation runs under `tests/skill_eval` with `CAIRN_SKILL_EVAL=1` (R20).

**Target Platform**: Claude Code on macOS and Linux consultant workstations.

**Project Type**: An agent skill plus a helper script, shipped as framework assets of the
existing `cairn` package.

**Performance Goals**: `charter.py status` and `check` finish in under 1 s on an engagement
with about 2,000 markdown files. The time goals for the session itself (SC-001: under 30
minutes; SC-002: under 10 minutes) depend on the interview, not on compute.

**Constraints**:
- Never reads `10-sources/`.
- Never reads `engagement.md` in the conversation (R7).
- No network access and no web or library research (FR-038).
- No real client name in charter files when a code name is set.
- The script runs on Python 3.9.
- `SKILL.md` stays at about 250 lines or fewer, with the detail in `reference/`.

**Scale/Scope**: Typically 5–15 questions, up to about 30 hypotheses, about 10 assumptions,
up to about 30 stakeholders and about 10 lenses or criteria. Revision sessions happen
about weekly over a four-week engagement.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / rule | How this plan complies | Status |
|---|---|---|
| I. Text-first | The skill is a folder with `SKILL.md`, reference files and one script. The script is used only where a deterministic check beats instructions: ID assignment, link validation, and a two-file consistent write (R2). It reads and writes plain markdown only, with no database or server. | Pass |
| II. Originals immutable | The skill and the script never open anything under `10-sources/` (R6). FR-021 adds that nothing in `raw/` is modified. | Pass |
| III. Atomic, cited evidence | Questions, hypotheses and assumptions are framing objects, not evidence claims. A question asserts nothing. A hypothesis is a claim *to be tested* (`active` means "being worked", not "true"). An assumption is by definition held without direct evidence. They come from the consultant (`consultant-note`) and cite no source (FR-019). Linking them to evidence is later skills' job (`supported_by`/`contradicted_by`, `test-hypothesis`). See Complexity Tracking. | Pass (confirmed in clarification 2026-11-03) |
| IV. Provenance and inference | Every item has `origin` (`consultant-note` or `llm-inference`), `confidence` and a reason. Kept suggestions are `llm-inference`, with a reason starting "Suggested by `charter`". `inference_confirmed` is never set (FR-036). | Pass |
| V. Stable IDs, link by ID | Next free ID is computed from every mention across the engagement (R9). No reuse. Links are quoted ID lists. Duplicates and malformed IDs are reported, never renumbered. | Pass |
| VI. Never delete, supersede | Amend, clarify, supersede, correct, reject, relink and scope change are defined in one convention (contracts/change-convention.md). Every event except an in-session amend is logged with date, reason and trigger. Old text is kept on the item or in a quoted changelog block. `refs` flags every linked object. | Pass |
| VII. Agents propose (NON-NEGOTIABLE) | All new items are `proposed`, from `_templates/`. Status changes happen only on the consultant's explicit instruction in the session (FR-034). `client-ready` is never set, and `check` reports it as a problem. Charter entries go to `00-charter/` rather than `_inbox/`, because the pipeline routes stage 1 there directly. | Pass |
| VIII. Confidentiality (NON-NEGOTIABLE) | No client documents are read. The real client name is kept out of the conversation (R7) and out of the files (`real-name-leak` check). Model use is settled first and recorded in both places. A one-time paste reminder is given. No network or research. The script outputs IDs only for non-charter objects. Fixtures and evaluations are synthetic, and the trial engagement stays local. | Pass |
| Canonical layout | No folders are added. The skill writes only to `00-charter/`, `60-log/changelog.md` and two fields of `engagement.md`. | Pass |
| Skill Contract 1–6 | (1) `raw/` untouched. (2) No source-based claims are written. See III. (3) Suggestions are marked `llm-inference`. (4) Items are `proposed`, from templates. (5) Next free IDs, ID-only links. (6) Never `client-ready`. | Pass |
| Workflow: spec-driven, minimal | Spec and clarifications exist. Data-model changes are limited to what FR-005/015/024/026/030/035 need, and every affected template and the 001 docs are updated together. | Pass |
| Workflow: validation on known outcomes | SC-008 is validated on the anonymized Phase 1 trial engagement, held locally (quickstart §8). Synthetic fixtures are used for everything committed. | Pass |
| Review gate | The PR checklist includes running `check` on sample output (provenance, `proposed`, ID-only links), plus the rule that charter items carry no citations (III note). | Pass |

**Note on Principle III**: The constitution says "every claim written by a skill MUST cite a
source ID" and "a claim without a citation MUST NOT be promoted to active". This plan reads
"claim" as an evidence claim: an observation, or anything built on observations. Charter
items are framing, and the spec requires that they cite no source (FR-019). Approving a
hypothesis makes it the working hypothesis. It doesn't assert it is true. If the project
owner reads III differently, the options are a constitution PATCH clarifying "claim", or
changing FR-034 so that approval of hypotheses and assumptions is deferred until evidence
exists. Confirmed by the project owner in clarification (2026-11-03).

**Post-design re-check (after Phase 1)**: Still passes. The design adds no folders and no
runtime dependencies. The only deterministic component (the script) is local, has no
network access, never touches `10-sources/`, and outputs IDs only for non-charter
objects. The template changes are additive, so existing engagements stay valid (new fields
are treated as empty when missing).

## Project Structure

### Documentation (this feature)

```text
specs/002-charter-skill/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R22
├── data-model.md        # Phase 1: model changes, charter/scope/items, check & gap codes
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── charter-skill.md       # invocation, session flow, outputs, never-do list, end summary
│   ├── charter-script.md      # charter.py commands, JSON output, exit codes
│   └── change-convention.md   # FR-030 shared convention (shipped verbatim in the skill)
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/cairn/
├── __init__.py                          # __version__ 0.1.0 → 0.2.0 (R22)
└── assets/
    ├── skills/
    │   └── charter/                     # NEW (replaces .gitkeep)
    │       ├── SKILL.md
    │       ├── reference/
    │       │   ├── interview.md
    │       │   ├── review-and-revise.md
    │       │   ├── change-convention.md # == specs/002-charter-skill/contracts/change-convention.md
    │       │   └── formats.md
    │       └── scripts/
    │           └── charter.py           # stdlib, Python 3.9+
    ├── templates/*.md                   # + change_reason, change_trigger (all 12); hypothesis + confirm_if, reject_if
    └── seed/
        ├── engagement.md                # + model_use_notes
        ├── 00-charter/scope.md          # + approval/notes front matter, In/Out scope, Constraints, Restrictions line
        └── 60-log/changelog.md          # guidance → change convention

specs/001-engagement-init/
├── data-model.md                        # §2, §3.1, §3.2 updated for the new fields
└── contracts/engagement-record.md       # + model_use_notes; charter writes model_use via script

tests/
├── unit/
│   └── test_charter_script.py           # parser, IDs, links, gaps, refs, model-use, leak, 10-sources exclusion
├── integration/
│   ├── test_charter_bundle.py           # init ships charter; refresh adds it to a 0.1.0 engagement; template fields
│   ├── test_charter_golden.py           # check passes/fails on fixtures with expected codes
│   ├── test_init.py                     # UPDATED: bundled skill count, README skill list, no-skills case via fixture
│   └── test_refresh.py                  # UPDATED if version-dependent expectations change
├── fixtures/charter/                    # synthetic: empty/, drafted/, approved/, revised/, broken/, codename/
└── skill_eval/                          # opt-in (CAIRN_SKILL_EVAL=1): scenarios + runner over `claude -p --resume`
    ├── conftest.py
    ├── scenarios/*.yaml
    └── test_scenarios.py
```

**Structure Decision**: No new package code. The feature lives in framework assets, which
`init` and `refresh` already distribute. The script is self-contained inside the skill
folder, so each engagement uses the copy pinned to its own framework version (R3). Tests
import it by path from `src/cairn/assets/skills/charter/scripts/` for unit tests, and run
it as a subprocess against fixture engagements for integration tests.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| Principle III read as applying to evidence claims, not to charter framing items (confirmed 2026-11-03) | FR-019 requires uncited, consultant-sourced items, and US3 requires approving them to `active` | Requiring citations would make the charter wait for ingestion, which reverses the pipeline (stage 1 comes before stage 2), and the clarification rules out reading kickoff documents |
| A helper script inside the skill (about 400 lines expected) | SC-003/SC-004 need 100% well-formed items and two-way links. ID numbering must count hand edits and mentions across the engagement. The real client name must stay out of the conversation. | Instructions only can't guarantee the 100% targets. A `cairn` subcommand would tie the skill to the installed CLI version and fail for analysts without `cairn`. |
| New standard fields on all 12 templates | FR-024/FR-026 require the reason to stay on the item, and FR-030 makes the convention shared across object types | Adding them to Q/H/A only would force a second data-model change when `record-change` lands |

## Clarifications Applied (2026-11-03)

- **Principle III**: confirmed. Its citation rule applies to evidence claims. Charter
  questions, hypotheses and assumptions go `active` on approval without a citation (spec
  Clarifications; Assumptions).
- **In-session amend rule (R10)**: confirmed and written into FR-021.
- **Approval after revisions (R18)**: the charter stays approved. The summary counts items
  proposed since the last approval (FR-035).
- **Constraints**: a Constraints section in `scope.md`, as designed in R15 (FR-013).
