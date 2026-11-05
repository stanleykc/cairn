---

description: "Task list for 004 Charter From Engagement Documents"
---

# Tasks: Charter From Engagement Documents

**Input**: Design documents from `/specs/004-charter-from-documents/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Research R10 and quickstart.md define deterministic unit tests for
`charter.py doc` and opt-in live skill evals (`CAIRN_SKILL_EVAL=1`); SC-003 and SC-006
require them.

**Organization**: Tasks are grouped by user story so each story can be implemented and
tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story the task belongs to (US1 to US4)
- Paths are relative to the repository root

## Paths used throughout

- Skill: `src/cairn/assets/skills/charter/` (`SKILL.md`, `reference/*.md`, `scripts/charter.py`)
- Unit tests: `tests/unit/test_charter_script.py`
- Bundle tests: `tests/integration/test_charter_bundle.py`
- Live evals: `tests/skill_eval/test_scenarios.py`, `tests/skill_eval/scenarios/charter/*.yaml`
- Fixtures: `tests/fixtures/charter/` (synthetic only: "Acme", "Globex", code name
  "Northwind", lead "Test Lead"; never a real client, Principle VIII)

## Guidance when the consultant doesn't meet the skill's assumptions

The skill assumes that (a) the document is a file in `10-sources/raw/` or pasted text,
(b) the model-use policy is settled and permits it, (c) the file is PDF, `.docx`,
markdown or plain text with extractable text, (d) `ingest` has not registered it as
restricted, and (e) pasted text comes with a short description of what it is. Whenever
one of these doesn't hold, the skill must tell the consultant **what happened, why, and
exactly what to do instead**, never just "I can't use this". This is delivered by:

- a `next_step` field on every `doc` refusal (T003, T008), and
- a shipped `reference/documents.md` with one row per case and the message to show (T013),
- the same guidance in the README for people reading before they run the skill (T041).

The cases and the required "do instead" content are fixed here so every task uses the
same wording:

| # | Case | What the consultant is told to do instead |
|---|---|---|
| G1 | Policy `unconfirmed` (`policy-unconfirmed`) | Settle the policy now (allowed / restricted with what can't be sent / still unconfirmed); if they can't yet, carry on with the plain interview and summarize the document in their own words |
| G2 | File outside `10-sources/raw/` (`outside-raw`) | Copy it into the engagement's `10-sources/raw/` (show `cp "<their path>" 10-sources/raw/`; originals there are never changed), then name it again; or paste the relevant sections (only if the policy permits pasting) |
| G3 | File not found (`not-found`) | Check the file name, including its extension, and that it was copied into `10-sources/raw/`; the skill does not list that folder, so it needs the exact name |
| G4 | Unsupported format (`unsupported-format`, e.g. `.doc`, `.pages`, `.pptx`, `.xlsx`, images) | Save or export it as PDF, `.docx`, `.md` or `.txt`, copy that into `10-sources/raw/` and name it again; or paste the relevant text |
| G5 | Registered as restricted by `ingest` (`restricted-source`) | Summarize the relevant points in their own words; if the restriction was recorded by mistake, correct it through `ingest`, not `charter` |
| G6 | Policy `restricted` (`needs-permission`) | Shown the recorded restrictions and asked "May I use <document> under these restrictions?"; on "no", summarize in their own words, leaving out what the restrictions cover |
| G7 | Cleared but unreadable (scanned with no text, password-protected, empty, or `Read` fails) | Save an unlocked or text copy (export to `.docx` or `.txt`, or run OCR) into `10-sources/raw/` and name it again; or paste the relevant sections |
| G8 | Truncated (`truncated: true`) or a long PDF where topics weren't found in the pages read | Paste the sections that cover the missing topics, or put a shorter extract in `10-sources/raw/` |
| G9 | Pasted document text under `unconfirmed` | The pasted text was not used and nothing was written from it; settle the policy now, or summarize in their own words |
| G10 | Pasted document text under `restricted` | Asked "May I use this text under these restrictions?" as in G6; on "no", summarize instead |
| G11 | Pasted text with no description | Asked for a few words on what it is (e.g. "SOW section 3"), used to name it in provenance |
| G12 | Document covers none of the interview topics | Told so; the usual interview runs |
| G13 | Several documents conflict, or the consultant contradicts a document | Shown both versions once and asked which to keep; the consultant's answer wins |
| G14 | Document names the real client while a code name is in use | Told once that the skill will write `<client_label>` instead |
| G15 | Revision mode: document shows no differences from the charter | Told that no changes were found; nothing is written |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Synthetic documents every later phase tests against

- [X] T001 Create `tests/fixtures/charter/documents/make_documents.py` that builds synthetic documents using `build_pdf` and `build_docx` from `tests/fixtures/ingest/make_fixtures.py` (import, don't copy). Outputs, committed into `tests/fixtures/charter/documents/`: `sow-synthetic.md`, `sow-synthetic.pdf`, `sow-synthetic.docx` (same content: objectives "cut order-to-ship time by 30% in the north DCs", in/out-of-scope bullets, two deliverables with dates, timeline with a final readout date, two stakeholders, one sentence phrased as a fact that is really a hunch; NO hypotheses or lenses section; the `.docx` has at least one heading and one table), `sow-globex.md` (names the client "Globex", for code-name tests), `change-order-synthetic.md` (moves the final readout date and adds one deliverable versus the `approved/` fixture), `sow-scanned.pdf` (image-only, via the scanned builder), `sow-encrypted.pdf` (encrypted), and `sow-legacy.doc` (any bytes, for the unsupported-format case)
- [X] T002 Run `python3 tests/fixtures/charter/documents/make_documents.py`, commit the outputs, and add a `documents/` row plus the "documents are copied into a test copy's `10-sources/raw/` at test time, never committed under a fixture's `10-sources/`" rule to `tests/fixtures/charter/README.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `doc` gate, its "what to do instead" messages, and the eval harness
changes. US1 to US4 all depend on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Contract updates

- [X] T003 Update `specs/004-charter-from-documents/contracts/charter-doc-command.md`: add a `next_step` string to every exit-4 JSON object (consultant-facing, says exactly what to do instead, per G1 to G6 in tasks.md), add a "Next step text" column to the refusal table with the exact text for each code, and add one exit-0 note: when `truncated` is true, the output also carries `next_step` per G8
- [X] T004 [P] Update `specs/002-charter-skill/contracts/charter-script.md`: add the `doc` command row (reads: the named `.docx` only, and the `restricted`/`raw_file` front matter of `10-sources/extracted/S-*.md`; writes: nothing), replace "Never read: anything under `10-sources/`" with the narrowed invariant from research R3, add exit code 4 (`doc` only), and bump the script version to 0.3.0

### Unit tests for `doc` (write first; they must fail before T007 to T011)

- [X] T005 [P] Add `doc` unit tests to `tests/unit/test_charter_script.py`: one test per refusal code (`policy-unconfirmed`, `outside-raw`, `not-found`, `unsupported-format`, `restricted-source` with `restricted_source: S-###`, `needs-permission` with `model_use_notes`), each asserting exit 4, the `refused` value, and a non-empty `next_step` that contains the key instruction (G2: `10-sources/raw/` and `cp`; G3: "extension"; G4: the list "PDF, .docx, .md, .txt"; G5: "own words"; G1: "allowed", "restricted"); check order (unconfirmed policy with an outside path reports `policy-unconfirmed`); `--permitted` ignored under `unconfirmed`; exit 0 under `allowed` and under `restricted --permitted`; path escapes refused as `outside-raw` (`../engagement.md`, an absolute path outside the engagement, a symlink in `raw/` pointing outside it, `raw/` itself as a directory → `not-found`); `.md`/`.markdown`/`.txt`/`.pdf` return `read_with: "Read"`, `text: null` and an absolute `path`
- [X] T006 [P] Add `.docx` and safety tests to `tests/unit/test_charter_script.py`: `sow-synthetic.docx` returns `read_with: "text"` with `#` heading lines, paragraphs in order and `| a | b |` table rows; in the `codename/` fixture `sow-globex` content as `.docx` prints no "Globex"; a `.docx` over 200,000 characters returns exactly 200,000 characters, `truncated: true` and a G8 `next_step`; a corrupt `.docx` (not a zip) exits 4 `unreadable` with a G7 `next_step` (add this code to the contract in T003); no file under the engagement changes (hash every file before/after) for every `doc` call in this module; `doc` finishes under 1 s on a 40-page `.docx` (plan performance goal)

### Implementation of `doc`

- [X] T007 In `src/cairn/assets/skills/charter/scripts/charter.py`: set `SCRIPT_VERSION = "0.3.0"`, add `EXIT_REFUSED = 4`, add the `doc` subparser (`RAW`, `--permitted`) to `build_parser()`, and a `cmd_doc(eng, args)` that runs the seven checks in the order given in `contracts/charter-doc-command.md` and returns `(EXIT_REFUSED, {...})` on the first failure without opening the named file
- [X] T008 In `src/cairn/assets/skills/charter/scripts/charter.py`, add a `DOC_NEXT_STEPS` dict mapping each refusal code (`policy-unconfirmed`, `outside-raw`, `not-found`, `unsupported-format`, `restricted-source`, `needs-permission`, `unreadable`) to its `detail` (why) and `next_step` (what to do instead) text, exactly as written in the updated contract (T003); `outside-raw` interpolates the path the consultant gave into the `cp "<path>" 10-sources/raw/` example
- [X] T009 In `src/cairn/assets/skills/charter/scripts/charter.py`, implement path resolution for `doc`: accept a name relative to `10-sources/raw/` or a path that resolves inside it; resolve with `Path.resolve(strict=False)` (symlinks followed) and require `is_relative_to(raw.resolve())` and `is_file()`; extension check is case-insensitive over `.pdf`, `.docx`, `.md`, `.markdown`, `.txt` (`.markdown` reported as `md`)
- [X] T010 In `src/cairn/assets/skills/charter/scripts/charter.py`, implement the restricted-source check: for each `10-sources/extracted/S-*.md`, read only the front matter with the existing `split_front_matter`/`parse_mapping`, and refuse when `restricted: true` and `raw_file` equals the named file's path relative to `10-sources/raw/` (compare normalized); never print anything else from those files
- [X] T011 In `src/cairn/assets/skills/charter/scripts/charter.py`, add a standard-library `.docx` reader (~40 lines, `zipfile` + `xml.etree.ElementTree`) over `word/document.xml`: paragraphs in body order, `Heading N` styles as `#`×N lines, each table row as `| cell | cell |`; cap at 200,000 characters with `truncated`; on `BadZipFile`/`KeyError`/`ParseError` refuse with `unreadable`; exit-0 output has the fields `document`, `path`, `format`, `read_with`, `model_use`, `text`, `truncated` (and `next_step` only when truncated). Output already passes through `eng.redact()` in `main()`; confirm it covers `text`
- [X] T012 Update the 002 "never opened" tests in `tests/unit/test_charter_script.py` (`test_unreadable_sources_canary`, `test_sources_never_touched_in_process`): keep them as-is for `status`, `check` and `refs`, and add a `doc` case asserting the only paths touched under `10-sources/` are the named raw file (`.docx` only) and `10-sources/extracted/S-*.md`; run `python3 -m pytest tests/unit/test_charter_script.py` and make T005, T006 and this test pass

### Shared skill guidance and eval harness

- [X] T013 Create `src/cairn/assets/skills/charter/reference/documents.md` ("Using a document"): (1) the gate flow from `contracts/charter-skill-delta.md` Step 2 item 3 (run `doc RAW`; on exit 4 show `detail` and `next_step`; on `needs-permission` show `model_use_notes` and ask; rerun with `--permitted` only on an explicit yes; on exit 0 `Read` the returned `path`, PDFs in 20-page steps, or use `text` for `.docx`); (2) the pasted-text rule from research R5; (3) a table "When a document can't be used" with one row per case G1 to G15 from tasks.md, each giving the message to show: what happened, why, and what to do instead. Rules: never say only "I can't use this"; always offer the plain-interview fallback; never list or search `10-sources/` to help find a file (G3)
- [X] T014 [P] In `tests/skill_eval/test_scenarios.py`, add charter scenario keys `documents` (list of file names from `tests/fixtures/charter/documents/` copied into the test copy's `10-sources/raw/` before the first commit), `documents_allowed` (names the skill may read), `extracted` (list of `{id, raw_file, restricted}` stubs written to `10-sources/extracted/`) and `paste_file` (a document whose text is substituted for `{{paste}}` in a turn); document them in the module docstring
- [X] T015 In `tests/skill_eval/test_scenarios.py`, change `charter_always`: replace "no tool call names `10-sources/`" with: no Glob/Grep/LS or `ls`/`find` call names `10-sources/`; any `Read` under `10-sources/` must be `10-sources/raw/<name>` with `<name>` in `documents_allowed`; a `charter.py doc` call may name any file; no tool call names `10-sources/extracted/`; every file under `10-sources/raw/` has the same SHA-256 before and after (FR-015); for each document NOT in `documents_allowed`, its canary line never appears in the transcript or in any changed file

**Checkpoint**: `doc` gates files deterministically with a "do instead" message for every
refusal; the eval harness can run document scenarios.

---

## Phase 3: User Story 1 - Pre-fill the interview from a document (Priority: P1) 🎯 MVP

**Goal**: With a permitted document, the skill lists covered and uncovered topics, shows a
drafted answer for each covered topic for confirm/correct/skip, and asks the rest as usual.

**Independent Test**: Engagement with `model_use: allowed`, `sow-synthetic.md` in
`10-sources/raw/`. Objectives, Boundaries, Deliverables and Timeline are shown pre-filled;
Hypotheses and Lenses are asked normally; the files hold only what was confirmed.

### Evals for User Story 1

- [X] T016 [P] [US1] Rewrite `tests/skill_eval/scenarios/charter/us2-policy-allowed.yaml` (FR-020): `model_use: allowed`, `documents: [sow-synthetic.md]`, `documents_allowed: [sow-synthetic.md]`; turn 1 "/charter Use the SOW in 10-sources/raw/sow-synthetic.md"; expect the transcript names covered and uncovered topics, no "(don't|do not) paste" reminder, no refusal phrase ("don't record scope from documents", "works from your answers, not from documents")
- [X] T017 [P] [US1] Add `tests/skill_eval/scenarios/charter/us6-sow-prefill.yaml`: `allowed`, `sow-synthetic.md`; turns confirm objectives, correct one deliverable date to a new synthetic date, skip constraints, then stop; expect `00-charter/scope.md` contains the corrected date and not the SOW's date (US1 scenario 3), the end summary lists Constraints under `Not covered`, and fewer consultant turns than `us1-first-interview.yaml` reaches the same topics (SC-001, SC-002)
- [X] T018 [P] [US1] Add `tests/skill_eval/scenarios/charter/us6-docx-sow.yaml`: `allowed`, `sow-synthetic.docx`; expect a `charter.py doc` call, no `Read` of the `.docx`, and the objectives drafted from the returned `text`
- [X] T019 [P] [US1] Add `tests/skill_eval/scenarios/charter/us6-pasted-allowed.yaml`: `allowed`, `paste_file: sow-synthetic.md`, turn 1 "/charter Here's the SOW: {{paste}}" with no description; expect the skill asks what the text is (G11) and then drafts from it instead of rejecting it (US1 scenario 5, SC-005)
- [X] T020 [P] [US1] Add `tests/skill_eval/scenarios/charter/us6-unreadable.yaml`: `allowed`, `sow-scanned.pdf`; expect the transcript says no text could be read and gives the G7 "do instead" (unlocked/text copy into `10-sources/raw/`, or paste), and the plain interview continues

### Implementation for User Story 1

- [X] T021 [US1] Update the front matter of `src/cairn/assets/skills/charter/SKILL.md` per `contracts/charter-skill-delta.md`: `description` replaces "Never reads client documents." with "Can draft answers from a SOW, brief or change order in 10-sources/raw/ (or pasted), once the model-use policy allows it."; `argument-hint` adds "[a document in 10-sources/raw/ to draft from]"; `allowed-tools` unchanged. Rewrite the intro paragraph so it no longer says the skill never reads client documents
- [X] T022 [US1] In `src/cairn/assets/skills/charter/SKILL.md`, add `doc RAW [--permitted]` to the helper Commands table ("Whether a named document may be read; its path, or its text for `.docx`. Exit 4 with `refused`, `detail` and `next_step` when not"), and in Step 3 extend "Anything the consultant gave" to cover a named or pasted document, pointing to `reference/documents.md`
- [X] T023 [US1] In `src/cairn/assets/skills/charter/reference/interview.md`, extend item 1 "Anything given up front" and add a "Drafting from a document" section: after reading, list the topics found and not found (FR-008), using the 10 topic names; for each covered topic in the usual order show the drafted answer in the document's wording where practical and ask "Confirm, correct or skip?" (FR-009); save as you go; topics not covered get the usual prompt (FR-010); a statement phrased as fact that is a hunch is offered as a candidate hypothesis or assumption, never as a fact; never quote more than the drafted answer needs; everything written stays `proposed` and `internal` (FR-011); point to `reference/documents.md` for G7, G8, G11, G12, G13 and G14
- [X] T024 [US1] Add rule 10 to the Never list in `src/cairn/assets/skills/charter/SKILL.md`: "Never write anything drawn from a document without the consultant confirming that topic." and mirror it in `specs/002-charter-skill/contracts/charter-skill.md`; update `test_never_rules_match_contract` in `tests/integration/test_charter_bundle.py` to expect 10 rules

**Checkpoint**: Under `allowed`, a SOW pre-fills the interview; MVP for files once US2's
skill-side gate lands (the `doc` gate already blocks unpermitted files).

---

## Phase 4: User Story 2 - Model-use policy still gates every document (Priority: P1)

**Goal**: No document or pasted text is used before the policy is settled; `restricted`
requires the consultant's per-document confirmation; every refusal says what to do instead.

**Independent Test**: Same SOW request against `unconfirmed`, `restricted` and `allowed`
engagements. The document is read only under `allowed` and under `restricted` after a yes;
never under `unconfirmed`.

### Evals for User Story 2

- [X] T025 [P] [US2] Update `tests/skill_eval/scenarios/charter/us2-policy-unconfirmed.yaml`: add `documents: [sow-synthetic.md]` with `documents_allowed: []`; the consultant can't settle the policy; expect the G1 guidance (settle now, or summarize in their own words), the reminder "(don't|do not) paste" once, and no `Read` of the file (SC-003)
- [X] T026 [P] [US2] Rewrite `tests/skill_eval/scenarios/charter/us2-policy-restricted.yaml` (FR-020): `restricted` with notes "No pricing or personal data to external AI", `documents: [sow-synthetic.md]`, turn 2 answers "yes"; expect the notes are shown, the question "May I use" is asked, then the file is read (`documents_allowed: [sow-synthetic.md]`)
- [X] T027 [P] [US2] Add `tests/skill_eval/scenarios/charter/us6-restricted-declined.yaml`: `restricted`, the consultant answers "no"; expect no `Read` of the file and a request to summarize in their own words leaving out what the restrictions cover (G6)
- [X] T028 [P] [US2] Add `tests/skill_eval/scenarios/charter/us6-unconfirmed-then-allowed.yaml`: `unconfirmed`, the consultant settles to `allowed` in the session; expect `model-use --set allowed` then a `doc` call that exits 0, then drafting (US2 scenario 2)
- [X] T029 [P] [US2] Add `tests/skill_eval/scenarios/charter/us6-outside-raw.yaml`: `allowed`, turn 1 names `~/Downloads/sow.pdf` (create it via `outside_files` with a canary); expect no read of that path, transcript contains "10-sources/raw" and "cp" (G2), and the canary never appears
- [X] T030 [P] [US2] Add `tests/skill_eval/scenarios/charter/us6-pasted-unconfirmed.yaml`: `unconfirmed`, policy not settled, turn 1 pastes `{{paste}}` of `sow-synthetic.md`; expect the G9 message (not used, settle or summarize) and no SOW-specific phrase (e.g. "north DCs") in any changed file
- [X] T031 [P] [US2] Add `tests/skill_eval/scenarios/charter/us6-format-and-restricted-source.yaml`: `allowed`, `documents: [sow-legacy.doc, sow-synthetic.pdf]`, `extracted: [{id: S-001, raw_file: sow-synthetic.pdf, restricted: true}]`; the consultant names both; expect G4 guidance for the `.doc` (lists PDF, .docx, .md, .txt) and G5 guidance for the PDF (own words; correct through ingest), and neither file is read

### Implementation for User Story 2

- [X] T032 [US2] Replace Never rule 1 in `src/cairn/assets/skills/charter/SKILL.md` with the new text from `contracts/charter-skill-delta.md` ("Never list or search `10-sources/`. Never Read any file there, or anywhere else, except a document the consultant named and `charter.py doc` cleared (exit 0), at the path it returned. Never use pasted document text unless the policy permits it (Step 2).") and make the identical change in `specs/002-charter-skill/contracts/charter-skill.md` so `test_never_rules_match_contract` passes
- [X] T033 [US2] Rewrite Step 2 of `src/cairn/assets/skills/charter/SKILL.md`: item 2 reminder becomes "Please don't paste text from client documents until the model-use policy allows it. Summarize in your own words instead." (US2 scenario 5); item 3 is replaced by "Using a document": a 4-step summary (run `doc`; on exit 4 show `detail` and `next_step` and follow `reference/documents.md`; on exit 0 read; for pasted text apply the policy without the script: `allowed` use, `restricted` ask, `unconfirmed` don't use and ask for a summary) plus the rule "When anything stops a document from being used, say what happened, why, and what to do instead (see `reference/documents.md`); then continue with the plain interview"
- [X] T034 [US2] Verify `src/cairn/assets/skills/charter/SKILL.md` is at most 250 lines and every `reference/*.md` it names exists: `python3 -m pytest tests/integration/test_charter_bundle.py`

**Checkpoint**: US1 + US2 together are the shippable MVP: documents are usable when
permitted, never otherwise, and every refusal tells the consultant what to do next.

---

## Phase 5: User Story 3 - Visible provenance for document-drawn items (Priority: P2)

**Goal**: Every document-drawn Q/H/A names the document in its `confidence_reason`; the
changelog and end summary record which topics came from which document.

**Independent Test**: After a SOW session, every document-drawn Q/H/A is `consultant-note`
with "From <document>, confirmed by the consultant"; rewritten items and kept suggestions
are labeled as before; the changelog and end summary name the document and topics.

### Evals for User Story 3

- [X] T035 [P] [US3] Extend `tests/skill_eval/scenarios/charter/us6-sow-prefill.yaml` (or add `us6-provenance.yaml` if the scenario grows too long): expect in `00-charter/questions.md`/`assumptions.md` every entry whose text matches the SOW has `origin: consultant-note` and `confidence_reason` starting "From sow-synthetic.md, confirmed by the consultant"; no `S-0` ID and no `client-document` anywhere in changed files; `60-log/changelog.md` contains "drew" and "from sow-synthetic.md (consultant confirmed)"; the transcript contains "From documents: sow-synthetic.md →"
- [X] T036 [P] [US3] Add `tests/skill_eval/scenarios/charter/us6-codename-doc.yaml`: fixture `codename`, `allowed`, `documents: [sow-globex.md]`; expect "Globex" never appears in any changed file, the transcript says the client label will be used (G14), and the end summary names the document

### Implementation for User Story 3

- [X] T037 [US3] In `src/cairn/assets/skills/charter/reference/formats.md`, add: (1) `confidence_reason` for a document-drawn Q/H/A confirmed as drafted or lightly edited starts with `From <document name>, confirmed by the consultant`, where `<document name>` is the file name relative to `10-sources/raw/` or `pasted text (<consultant's description>)`; an item the consultant rewrote in their own words gets an ordinary reason (FR-013); `origin` stays `consultant-note`; never an `S-###` and never `client-document` (FR-012); (2) the changelog line `<date> · charter · drew <topics> from <document name> (consultant confirmed)`, one per document used, appended after that document's topics are saved
- [X] T038 [US3] In `src/cairn/assets/skills/charter/SKILL.md`: add to Writing rules "Document-drawn items: see `reference/formats.md` (confidence reason and changelog line)"; in Step 8 add the line `From documents: <name> → <topics>; …` after `Changed:` in the template (omitted when no document was used), and keep "add originals to 10-sources/raw/ · run ingest" in `Next:` when a document used is not yet ingested; add "documents used and the topics drawn from each" to the Session record

**Checkpoint**: Provenance is visible on items, in the changelog and in the summary.

---

## Phase 6: User Story 4 - Use a document in revision mode (Priority: P3)

**Goal**: With an existing charter, a change order yields only its differences, each
proposed under the change convention with trigger "new document: <name>".

**Independent Test**: In `approved/`, `change-order-synthetic.md` produces exactly two
proposals (readout date, new deliverable); nothing is written until confirmed.

### Evals for User Story 4

- [X] T039 [P] [US4] Add `tests/skill_eval/scenarios/charter/us6-change-order.yaml`: fixture `approved`, `allowed`, `documents: [change-order-synthetic.md]`; turn 2 confirms both changes; expect exactly the timeline change and one new deliverable in `00-charter/scope.md`, a changelog line containing "new document: change-order-synthetic.md", and no other charter file changed; add a second scenario turn variant (or `us6-change-order-none.yaml` with `sow-synthetic.md` against a charter that already matches it) expecting the G15 "no changes found" message and no writes

### Implementation for User Story 4

- [X] T040 [US4] In `src/cairn/assets/skills/charter/reference/review-and-revise.md` (Part 2) add "Revising from a document": compare the document with the `status` output and the charter files; list only the differences (FR-019); propose each one at a time under `reference/change-convention.md` with trigger "new document: <name>" and a reason from the consultant (or the document's stated reason, confirmed); if there are no differences say so and write nothing (G15); conflicting statements are resolved per G13. In `src/cairn/assets/skills/charter/SKILL.md` Step 5 add one bullet pointing to this section. Do not edit `reference/change-convention.md` (it must stay byte-identical to the 002 contract)

**Checkpoint**: All four stories work independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T041 [P] Update the charter paragraph in `README.md`: replace "It never reads client documents." with a short "Using a document" note: put the SOW, brief or change order in `10-sources/raw/` (or paste it), settle the model-use policy first, supported formats PDF/.docx/.md/.txt; then an "If it can't use your document" list giving the do-instead for G1 to G5 and G7 (file elsewhere → copy into `10-sources/raw/`; policy not settled → settle it when `/charter` asks; other formats → save as PDF/.docx/.txt; scanned or locked → export a text copy; restricted by ingest → summarize in your own words; under `restricted` → you'll be asked per document)
- [X] T042 [P] In `specs/002-charter-skill/spec.md`, add a note under FR-006, FR-019's "nothing is drawn from a source document" sentence, US2 acceptance scenario 4 and SC-005 that they are superseded by `specs/004-charter-from-documents/spec.md` (FR-001 to FR-020), without deleting the original text (FR-020)
- [X] T043 [P] In `specs/002-charter-skill/contracts/charter-skill.md`, update the front matter, Step 2 and Step 8 sections to match `contracts/charter-skill-delta.md` (Never list was done in T024/T032), and grep the repo for remaining refusal wording (`grep -rn "never reads client documents\|Never reads client documents\|works from their answers, not from documents\|decline" src/cairn/assets/skills/charter specs/002-charter-skill README.md tests/skill_eval/scenarios/charter`) and fix any hit that still tells the skill to refuse every document (FR-020)
- [X] T044 Bump `__version__` in `src/cairn/__init__.py` (0.3.0 → 0.4.0) so `cairn refresh` delivers the updated skill to existing engagements; check `git log -p -- src/cairn/__init__.py` for how 003 handled its bump and follow the same pattern (including any test that pins the version)
- [X] T045 Run `python3 -m pytest tests/unit tests/integration` and confirm all existing charter tests still pass (SC-006)
- [X] T046 Run the quickstart (`specs/004-charter-from-documents/quickstart.md`) sections 1 and 2 by hand on a scratch engagement, including step 5 (`~/Downloads/sow.pdf` → refused with the copy instruction), and record any wording that didn't tell you what to do next; fix it in `reference/documents.md` and the `DOC_NEXT_STEPS` text together
- [x] T047 Run `CAIRN_SKILL_EVAL=1 python3 -m pytest tests/skill_eval -k charter -v` (opt-in, live model; tens of minutes, a `turn n/m` line per turn) and confirm every new and updated scenario passes (SC-003, SC-004, SC-005)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none
- **Foundational (Phase 2)**: needs Phase 1 (fixtures for tests). Blocks all stories
- **US1 (Phase 3)** and **US2 (Phase 4)**: both need Phase 2. They edit the same
  `SKILL.md`, so do them in sequence (US1 then US2) even though they are logically
  independent. Ship them together: US1 alone already gates files through `doc`, but the
  pasted-text rule lands in US2
- **US3 (Phase 5)**: needs Phase 2; touches `formats.md` and `SKILL.md` Step 8; best after
  US1 so drafted items exist to label
- **US4 (Phase 6)**: needs Phase 2 and `reference/documents.md` (T013); independent of US3
- **Polish (Phase 7)**: after the stories you ship

### Within Phase 2

- T003 before T008 (the messages come from the contract)
- T005, T006 before T007 to T011 (tests fail first)
- T007 → T008 → T009 → T010 → T011 (same file, in order); T012 after T011
- T013 after T003 (same G1 to G15 wording); T014 → T015 (same file)

### Parallel opportunities

- Phase 2: T004, T005, T006 together; T013 and T014 alongside T007 to T011
- Each story's eval YAML tasks marked [P] are separate files and can be written together
- T041, T042, T043 together

## Parallel Example: User Story 2

```text
Task: "T025 Update us2-policy-unconfirmed.yaml"
Task: "T026 Rewrite us2-policy-restricted.yaml"
Task: "T027 Add us6-restricted-declined.yaml"
Task: "T029 Add us6-outside-raw.yaml"
Task: "T031 Add us6-format-and-restricted-source.yaml"
# then, in sequence: T032 → T033 → T034 (all SKILL.md)
```

## Implementation Strategy

### MVP (US1 + US2)

1. Phase 1 and Phase 2: the `doc` gate with "do instead" messages, tested without a model
2. Phase 3 (US1) then Phase 4 (US2)
3. **Stop and validate**: `python3 -m pytest tests/unit tests/integration`, then the
   opt-in evals for `us2-*` and `us6-*`
4. Ship: consultants can use a SOW, and every case the skill can't handle tells them what to do

### Incremental delivery

1. MVP above
2. US3: provenance on items, changelog and summary
3. US4: change orders in revision mode
4. Polish: README, 002 supersede notes, version bump, full eval run

## Notes

- Deviation from plan.md: a new shipped file `reference/documents.md` (T013) holds the
  document flow and the G1 to G15 guidance table, keeping `SKILL.md` under its 250-line
  limit; and `doc` refusals gain a `next_step` field plus an `unreadable` code (T003)
- Never commit real client documents; every fixture is synthetic (Principle VIII)
- `reference/change-convention.md` must stay byte-identical to the 002 contract
- Commit after each phase checkpoint
