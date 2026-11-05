# Implementation Plan: Charter From Engagement Documents

**Branch**: `004-charter-from-documents` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-charter-from-documents/spec.md`

## Summary

Let `charter` draft interview answers from a SOW, brief or change order instead of
refusing it. Two conditions apply: the document is a file in `10-sources/raw/` (or pasted
text), and the model-use policy permits it. A new `charter.py doc` command makes the
policy, location and restricted-source checks deterministic, and returns `.docx` text.
The skill instructions replace the blanket refusal with the following flow: gate with
`doc`, read, list the covered topics, then confirm topic by topic. Document-drawn items
stay `consultant-note`, with the document named in the confidence reason and in the
changelog.

## Technical Context

**Language/Version**: Python 3.9+ for the helper script (standard library only, as in
002); skill instructions in Markdown

**Primary Dependencies**: None new. `zipfile` and `xml.etree` for `.docx`; Claude Code's
`Read` tool for PDF, markdown and text

**Storage**: Plain markdown files in the engagement folder (unchanged)

**Testing**: pytest (unit and integration); opt-in live skill evals (`CAIRN_SKILL_EVAL=1`)

**Target Platform**: macOS and Linux, wherever Claude Code and `python3` run

**Project Type**: CLI framework with bundled agent skills (`src/cairn/assets/skills/`)

**Performance Goals**: `doc` finishes in under 1 s for a 40-page `.docx`; a SOW session
takes at most half the consultant turns of one without a document (SC-002)

**Constraints**: No network; no writes by `doc`; no reading of a document before the
policy gate; the real client name is never printed when a code name is in use

**Scale/Scope**: One new helper command (~120 lines), edits to `SKILL.md` and three
reference files, updates to the 002 contract docs, and about 6 new or updated eval
scenarios

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / rule | Status | Notes |
|---|---|---|
| I. Text-first | ✅ | Files only; the script is limited to deterministic checks (R1) |
| II. Originals immutable | ✅ | `doc` never writes; the skill only reads (FR-015) |
| III. Atomic, cited evidence | ✅ | Charter items remain framing items with no source citation; Clarification Q2 keeps them `consultant-note`. No amendment needed |
| IV. Visible provenance | ✅ | The document is named in `confidence_reason`, the changelog and the end summary (R6) |
| V. Stable IDs | ✅ | Unchanged ID rules |
| VI. Never delete, supersede | ✅ | Revision mode uses the existing change convention, with a document trigger (R9) |
| VII. Agents propose (NON-NEGOTIABLE) | ✅ | Every document-drawn answer needs the consultant's confirmation; items stay `proposed`/`internal` (FR-009, FR-011) |
| VIII. Confidentiality (NON-NEGOTIABLE) | ✅ | Policy gate before any read; ingest's restricted registrations honored; files outside the engagement refused; code-name redaction; synthetic fixtures only |
| Skill contract 1 to 6 | ✅ | No raw/ writes; no evidence claims; inference marked; proposed; IDs; never client-ready |
| Canonical layout | ✅ | No change |

**Post-design re-check**: ✅ Still passes. One narrowing to record: the 002 helper
invariant "never opens anything under `10-sources/`" becomes "opens only the named raw
`.docx` and the `restricted`/`raw_file` front matter of extracted sources" (R3). This
deliberately revises the 002 contract, not a constitution deviation, so Complexity
Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-charter-from-documents/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── charter-doc-command.md
│   └── charter-skill-delta.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/cairn/assets/skills/charter/
├── SKILL.md                          # Never list, Step 2, Step 4/5 notes, end summary
├── reference/
│   ├── interview.md                  # drafted answers from a document
│   ├── formats.md                    # confidence_reason + changelog line
│   └── review-and-revise.md          # revision from a change order
└── scripts/charter.py                # new `doc` command, EXIT_REFUSED = 4, v0.3.0

specs/002-charter-skill/              # FR-006 / US2-4 note pointing to 004; contracts updated
├── spec.md
└── contracts/{charter-skill.md,charter-script.md}

tests/
├── unit/test_charter_script.py       # doc command tests; narrowed "10-sources never opened" test
├── fixtures/charter/documents/       # synthetic SOW (.pdf, .docx, .md), change order
└── skill_eval/
    ├── test_scenarios.py             # per-scenario documents_allowed
    └── scenarios/charter/            # updated us2-*; new us6-* document scenarios
```

**Structure Decision**: Single project. The change is confined to the bundled `charter`
skill, its tests and fixtures, and the 002 docs it supersedes. `ingest` is not modified.

## Complexity Tracking

No violations.
