# Implementation Plan: Ingest Skill

**Branch**: `003-ingest-skill` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-ingest-skill/spec.md`

## Summary

Ship the second Cairn skill, `ingest`, stage 2 of the pipeline. It turns PDFs, Word
documents, markdown, plain text and caption files in `10-sources/raw/` into one verbatim,
citable `S-###` source each. It enforces the model-use policy before anything is opened,
registers restricted files without opening them, and lets the consultant spot-check,
correct and approve the result.

The skill follows the `charter` pattern: a Claude Code skill folder in
`src/cairn/assets/skills/ingest/`, delivered by `cairn init` and `cairn refresh` with no
command changes. The key design choice is that **the helper script writes every verbatim
word, and the assistant only adds what needs vision or judgment** (research R2):

- `scripts/ingest.py` (standard library, Python 3.9+):
  - finds the engagement and reads the policy;
  - lists `raw/` and numbers sources;
  - extracts text deterministically:
    - PDF text layers via poppler's `pdftotext`, page by page, when poppler is installed
      (checked mode). Without poppler, the assistant copies each page's text from its own
      PDF reading, and the source is marked `fidelity: unchecked` and put first in review
      (unchecked mode, R4);
    - Word via its own `zipfile`/XML parser (headings, lists, tables, comments, tracked
      changes, chart data, images to a work folder);
    - markdown copied as is;
    - plain text with paragraph numbers;
    - VTT, SRT and text transcripts split into speaker turns;
  - checks fidelity word for word (`verify`);
  - owns every write that must keep the source, the index and the changelog in step
    (`finalize`, `set-status`, `restrict`).
- The assistant:
  - talks to the consultant (context, speaker names, restricted files);
  - views PDF pages and Word images to rebuild PDF tables, OCR scanned pages and describe
    charts, all marked `[!derived]`;
  - lists uncertain passages and fills in the metadata;
  - runs the review.
- The model-use policy is enforced twice: by the instructions, and by the script, which
  refuses `extract` under `unconfirmed`, or under `restricted` without per-file consent
  (R6).

Supporting changes:

- the source template gains the fields and body sections the spec needs (R8);
- the shared change convention gains `extraction-fix`, `restrict` and `remove-content`
  events (R14);
- framework version 0.3.0 (R20).

## Technical Context

**Language/Version**: Markdown skill instructions in Claude Code Agent Skills format. The
helper script is Python **3.9+**, standard library only, because it runs under the
consultant's `python3` (R3). The `cairn` package stays at Python 3.11+.

**Primary Dependencies**:
- Runtime, optional: **poppler** command-line tools (`pdftotext`, `pdfinfo`,
  `pdfimages`). They're recommended, not required (R4). With them, PDF text is extracted
  and checked word for word. Without them, PDFs are still ingested: the assistant copies
  the text, and the source is flagged `fidelity: unchecked` for spot-checking.
- Claude Code is the host assistant. Its Read tool provides PDF page vision and image
  vision.
- No new Python dependencies. Dev: `pytest` and `PyYAML` (existing).
- Opt-in evaluation: the `claude` CLI.

**Storage**: Engagement markdown files:
- `10-sources/extracted/S-###.md` (new);
- `10-sources/index.md` (rows);
- `60-log/changelog.md` (events);
- a temporary work folder, `.cairn/work/ingest/<S-ID>/`, for Word images (R13).

`10-sources/raw/` is read-only.

**Testing**: `pytest`:
- unit tests for every parser and command of `ingest.py`;
- integration tests for bundling and refresh, and golden synthetic sources checked with
  `verify`.

Fixtures (PDF, Word, transcripts) are generated at test time from synthetic text, so no
binaries are committed. PDF tests cover both modes: checked-mode tests skip without
poppler, and unchecked-mode tests hide poppler from `PATH`. An opt-in live-model evaluation
under `tests/skill_eval` (`CAIRN_SKILL_EVAL=1`) covers US1–US4 and the canary test (R18).

**Target Platform**: Claude Code on macOS and Linux consultant workstations.

**Project Type**: An agent skill plus a helper script, shipped as framework assets of the
existing `cairn` package.

**Performance Goals**:
- `status` and `verify` (all sources) finish in under 2 s on an engagement with 50
  sources and about 2,000 markdown files.
- `extract` of a 100-page text PDF or a 50-page Word document finishes in under 10 s.
- Session time is bounded by SC-006 (under 20 minutes hands-on for 10 sources). It
  depends on the consultant's answers and the vision pass, not on compute.

**Constraints**:
- Nothing under `10-sources/raw/` is ever written (SC-001).
- No file is opened under `unconfirmed`, and no restricted file is ever opened (SC-002).
- No network access and no web or library research (FR-008).
- The script's stdout never carries extracted text (R6).
- The assistant never reads `engagement.md` (002 R7).
- No real client name outside content regions when a code name is set.
- Read views at most 20 PDF pages per call, so long PDFs are processed in batches and can
  resume (R12).
- `SKILL.md` stays at about 250 lines or fewer, with the detail in `reference/`.

**Scale/Scope**: Typically 10–20 sources per engagement. Documents from 1 to about 200
pages. Transcripts up to about 2 hours (about 1,000 turns). Most sources are in English;
other languages are kept as they are.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / rule | How this plan complies | Status |
|---|---|---|
| I. Text-first | A skill folder with `SKILL.md`, reference files and one script. The script is used where a deterministic check beats instructions: verbatim extraction, ID assignment, fidelity checks, and consistent multi-file writes (R2). Plain markdown only. Status (`status`, `extraction_status`) lives in front matter. Poppler is a local tool, not a system of record. | Pass |
| II. Originals immutable | No command writes to `raw/`. Files are opened `rb`. Tests hash `raw/` around every command (SC-001). Every source records `extraction_method`, `uncertain_passages` and `fidelity`, so a PDF copied without poppler is never mistaken for a checked one. | Pass |
| III. Atomic, cited evidence | Ingest writes no claims. It makes every passage citable by a locator (page, heading path, ¶, timestamp, turn) so `extract-observations` can cite `S-###` + locator. The skill-written Description is labelled and excluded from citation (contracts/source-file.md, guarantee 3). | Pass |
| IV. Provenance and inference | Every source has `origin`, `confidence` and a reason (default `medium`, "trust not stated"). AI note-taker summaries are capped at `medium`. OCR, vision descriptions, chart data and diagram text are `[!derived]` callouts, with `derived: true` and the method recorded. Charts and photos get both text-in-image and a description (Skill Contract). | Pass |
| V. Stable IDs, link by ID | Next free `S-###` counts every mention outside `raw/` and outside content regions (R16). No reuse. `supersedes` holds IDs only. Duplicates and malformed IDs are reported, never renumbered. | Pass |
| VI. Never delete, supersede | New versions are new sources linked with `supersedes`. Old ones are kept and become `superseded` only on approval, with a logged event. Corrections keep the previous text in the callout and in the changelog (`extraction-fix`). Removing a restricted source's content is the one deletion the spec allows. It happens only on explicit instruction and is logged (`remove-content`). | Pass |
| VII. Agents propose (NON-NEGOTIABLE) | Every source is written `proposed` and `internal`. `active` and `rejected` happen only through `set-status`, after the consultant's explicit instruction. `client-ready` is never set, and `verify` flags it. Sources go to `10-sources/extracted/`, not `_inbox/`: the pipeline routes stage 2 there directly, and triage applies to observations. | Pass |
| VIII. Confidentiality (NON-NEGOTIABLE) | The policy is checked before any file is opened. Under `unconfirmed`, nothing is opened or written. Under `restricted`, the consultant gives consent per file. Restricted files are registered without being opened or hashed. The script enforces the same gates and never prints content (R6). The code name is used in all metadata, with a leak check (R17). There is no network access, and the work folder stays inside the engagement. Fixtures are synthetic, and the trial engagement stays local. | Pass |
| Canonical layout | No folders are added. Writes go to `10-sources/extracted/`, `10-sources/index.md`, `60-log/changelog.md` and `.cairn/work/` (internal and temporary). | Pass |
| Skill Contract 1–6 | (1) `raw/` untouched. (2) No evidence claims are written. Locators are provided for later citation. (3) Derived content is flagged. Ingest writes no inferences beyond the labelled description. (4) Sources are `proposed`, from `_templates/source.md`. (5) Next free IDs, links by ID only. (6) Never `client-ready`. | Pass |
| Skill-specific: ingest | Charts, diagrams and photos get text in the image plus a description, both derived. Tables are kept as markdown tables. Transcripts are split by speaker. Restricted sources are refused. Spreadsheets and image files are out of scope for this version (spec Assumptions). | Pass |
| Workflow: spec-driven, minimal | The spec has been clarified. Data-model changes are limited to what FR-018/023/031 and the edge cases need. The template, the change convention (all copies), the changelog seed and the 001/002 docs are updated together. | Pass |
| Workflow: validation on known outcomes | SC-007 is validated on the anonymized Phase 1 trial engagement, held locally (quickstart §9). Everything committed is synthetic. | Pass |
| Review gate | The PR checklist runs `verify` on golden sample sources (provenance, `proposed`, ID-only links, locators on every passage, derived flags). | Pass |

**Note on the Description section**: Principle IV says model-inferred content must carry
origin *LLM inference*. The Description isn't an object. It's a labelled, non-citable
note inside the source ("Written by `ingest`. Not part of the source."), and FR-021 forbids
conclusions in it. Later skills are contractually barred from citing it, so it can't
become evidence. The project owner confirmed keeping it (2026-11-05).

**Note on SC-004 and unchecked PDFs**: SC-004 is measured on the synthetic test set with
poppler present, where every source is `checked`. Without poppler, fidelity rests on the
assistant's copy plus the consultant's spot-check of sample pages. The source says so in
`fidelity: unchecked`, so the gap is visible, not silent.

**Post-design re-check (after Phase 1)**: Still passes. The design adds:
- one optional local tool (poppler), with an unchecked fallback;
- no folders;
- no Python runtime dependencies;
- a temporary work folder inside `.cairn/`.

Template changes are additive. No engagement has sources yet, so the `source_type` value
change needs no migration. The change-convention extension adds events without changing
existing ones, so charter behaviour is unaffected.

## Project Structure

### Documentation (this feature)

```text
specs/003-ingest-skill/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R20
├── data-model.md        # Phase 1: template changes, source, index, locators, callouts, events, verify codes
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── ingest-skill.md        # invocation, session flow, review flow, never-do list, end summary
│   ├── ingest-script.md       # ingest.py commands, JSON output, exit codes, file access
│   └── source-file.md         # the extracted source format and guarantees to later skills
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/cairn/
├── __init__.py                              # __version__ 0.2.0 → 0.3.0 (R20)
└── assets/
    ├── skills/
    │   ├── charter/reference/change-convention.md   # + extraction-fix, restrict, remove-content (R14)
    │   └── ingest/                          # NEW
    │       ├── SKILL.md
    │       ├── reference/
    │       │   ├── formats.md
    │       │   ├── source-record.md
    │       │   ├── review-and-correct.md
    │       │   └── change-convention.md     # byte-identical to charter's copy
    │       └── scripts/
    │           └── ingest.py                # stdlib, Python 3.9+
    ├── templates/source.md                  # new fields and body sections (R8)
    └── seed/60-log/changelog.md             # event list + subject form updated (R14)

specs/001-engagement-init/data-model.md      # source template row updated
specs/002-charter-skill/contracts/change-convention.md   # mirrors the updated convention

tests/
├── unit/
│   ├── test_ingest_script.py                # parsers, numbering, policy gate, verify, finalize, set-status, restrict, refs, raw/ immutability
│   └── test_ingest_parity.py                # shared parsing matches charter.py
├── integration/
│   ├── test_ingest_bundle.py                # init ships ingest; refresh 0.2.0 → 0.3.0 adds it; settings.json rule; template fields; convention copies identical
│   ├── test_ingest_golden.py                # verify passes/fails on golden sources with expected codes
│   ├── test_ingest_perf.py                  # status/verify/extract timing goals
│   └── test_init.py                         # UPDATED: bundled skill count 2, README lists ingest
├── fixtures/ingest/
│   ├── make_fixtures.py                     # generates synthetic PDFs, .docx, transcripts, notes
│   ├── golden/                              # synthetic engagements with expected sources (text only)
│   └── README.md
└── skill_eval/
    ├── conftest.py                          # UPDATED: per-skill scenario folders, raw/ hash and canary assertions
    └── scenarios/ingest/*.yaml              # NEW: US1–US4 and edge cases
```

**Structure Decision**: No new package code. The feature lives in framework assets, which
`init` and `refresh` already distribute, plus tests. The script is self-contained in the
skill folder, so each engagement uses the copy pinned to its own framework version (R3).
Unit tests import it by path. Integration tests run it as a subprocess against fixture
engagements.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| A larger helper script (about 1,200 lines expected: Word parser, transcript shapes, fidelity check) | FR-010 and SC-004 need 100% verbatim text, and SC-005 needs every passage locatable. Deterministic extraction is the only way to guarantee and verify that (R2). | The assistant retyping content can't be verified and costs a full document of output per source |
| Two PDF paths: poppler (checked) and the assistant's own reading (unchecked) | Nobody is blocked by a missing install, but the word-for-word guarantee is proven wherever poppler exists (R4) | Poppler required blocks PDFs on a fresh machine. Agent-only drops the automated fidelity check for every PDF. A pure-Python PDF parser is unreliable, and `pypdf` isn't available to the consultant's `python3`. |
| Parsing code duplicated from `charter.py` | Skills are refreshed independently and can't safely import each other (R3) | A shared module means refactoring `charter` in this feature. A parity test keeps the copies in step. The extraction is deferred to the third skill. |
| Change-convention extension (three new events) | FR-031 and the restrict-after-ingest edge case need logged events that don't fit `correct` or the existing triggers (R14) | Reusing `correct` would make `what-changed` mistake a transcription fix for a claim being disproved |

## Decisions Confirmed by the Project Owner (2026-11-05)

1. Poppler is optional, with an unchecked fallback (option B, R4).
2. The Description section is kept: a labelled, non-citable note of up to three sentences
   (FR-021). See the Constitution Check note.

No open points remain.
