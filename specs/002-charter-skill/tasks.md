---

description: "Task list for the Charter Skill (002-charter-skill)"
---

# Tasks: Charter Skill

**Input**: Design documents from `/specs/002-charter-skill/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R22), data-model.md, contracts/
(charter-skill.md, charter-script.md, change-convention.md), quickstart.md

**Tests**: Included. The plan (Testing) and research R20 call for `pytest` unit tests of the
script, integration tests for bundling, refresh and golden fixtures, and an opt-in live-model
skill evaluation (`CAIRN_SKILL_EVAL=1`). SC-003 and SC-004 are defined as "confirmed by an
automated check".

**Organization**: Tasks are grouped by user story so each story can be built and tested on
its own. The script (`charter.py`), `SKILL.md` and the golden test file grow across stories,
so tasks that touch them run in story order.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Every task names the exact file(s) it touches

## Path Conventions

Framework assets of the existing `cairn` package (plan.md → Project Structure):

- Skill: `src/cairn/assets/skills/charter/{SKILL.md,reference/,scripts/charter.py}`
- Templates and seeds: `src/cairn/assets/templates/`, `src/cairn/assets/seed/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/fixtures/charter/`, `tests/skill_eval/`
- Shorthand used below: **SCRIPT** = `src/cairn/assets/skills/charter/scripts/charter.py`,
  **SKILL** = `src/cairn/assets/skills/charter/SKILL.md`,
  **GOLDEN** = `tests/integration/test_charter_golden.py`,
  **UNIT** = `tests/unit/test_charter_script.py`

## Rules every task must respect

- SCRIPT is Python **3.9+**, standard library only: no `match`, no `X | Y` type unions at
  runtime, `from __future__ import annotations` at the top, never imports `cairn` (R3).
- SCRIPT never opens anything under `10-sources/` and never prints the text of objects
  outside `00-charter/` (R6). When a code name is set, the real `client` value never
  appears in any output (R7).
- All fixtures and scenarios use synthetic names only: "Acme", "Globex", code name
  "Northwind" (Principle VIII).
- Lists of IDs are written inline with quoted IDs: `["Q-001", "Q-002"]`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the skill folder and make the test helpers ready for a non-empty bundled
skill set.

- [X] T001 Delete `src/cairn/assets/skills/.gitkeep` and create SKILL with only the R21 front matter (`name: charter`; `description: "Frame or revise the engagement charter (scope, key questions, hypotheses, assumptions, stakeholders, lenses) by interviewing the consultant. Use at kickoff, or when the weekly steer changes questions, hypotheses or scope. Never reads client documents."` — one line, double-quoted, so `cairn`'s flat front matter reader can read it; `argument-hint: "[anything you already know: objectives, deadlines, hunches…]"`; `allowed-tools: Read, Edit, Write, Bash(python3 *charter.py*)`) followed by a `# Charter` heading. Do not add `.gitkeep` files under `reference/` or `scripts/` (every file under the skill folder is copied into engagements); those folders are created when their first file is added.
- [X] T002 Add a `bundled_skills=True` keyword to `fixture_assets` in `tests/conftest.py`. When `False`, remove every folder under `<copied assets>/skills/` before adding the `skills` argument's entries, so tests that need an exact skill set stay deterministic now that `charter` ships. Update the docstring.
- [X] T003 [P] Create `tests/fixtures/charter/README.md` describing the fixture set (`empty/`, `drafted/`, `approved/`, `revised/`, `broken/`, `codename/`), the synthetic-only naming rule, and that tests always copy a fixture to `tmp_path` before running SCRIPT against it (fixtures are never modified in place). Also note that the `10-sources/` canary file is created at test time, not committed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The data-model changes (data-model.md §1), the version bump, the 001 test updates,
and the script core (discovery, parser, scan, ID assignment) that every story's script
commands are built on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Data-model changes

- [X] T004 [P] In all 12 templates in `src/cairn/assets/templates/` (`assumption.md`, `decision.md`, `finding.md`, `hypothesis.md`, `issue.md`, `lesson.md`, `observation.md`, `opportunity.md`, `option.md`, `question.md`, `research.md`, `source.md`), add two lines directly after the `clarifies:` line, aligned with the existing comments: `change_reason: ""       # one line: reason for the latest supersede or reject` and `change_trigger: ""      # new-evidence | client-feedback | rethinking`.
- [X] T005 In `src/cairn/assets/templates/hypothesis.md` (after T004), add `confirm_if: ""            # evidence that would confirm it` and `reject_if: ""             # evidence that would reject it` directly after the `question:` line, and change the body text to "The working hypothesis in one sentence." (R14).
- [X] T006 [P] In `src/cairn/assets/seed/engagement.md`, add `model_use_notes: ""  # specific restrictions, free text` directly after the `model_use:` line, and add one bullet to the body's field explanations: `model_use_notes` holds what may or may not be sent, in the consultant's words; `""` when none is recorded (R8, data-model §4).
- [X] T007 [P] Update `src/cairn/assets/seed/00-charter/scope.md` (R15, data-model §3): front matter gains `model_use_notes: ""`, `charter_status: draft  # draft | approved`, `approved_on: ""`, `approved_by: ""` after `model_use`; under `## Boundaries` add `### In scope` and `### Out of scope`, each with a one-sentence seed guidance line; add `## Constraints` before `## Model use` with the guidance sentence "One bullet each, starting with **Budget**, **Timeline**, **Technology**, **Politics** or **Other**."; in `## Model use` add the line `Restrictions: none recorded.` directly after the `Current policy:` line. Keep `${model_use}` placeholders working with `init_cmd.py` substitution.
- [X] T008 [P] Rewrite the guidance in `src/cairn/assets/seed/60-log/changelog.md` to the shared convention (R12, contracts/change-convention.md §Changelog line): the line format `YYYY-MM-DD · <subject> · <event> · <reason> · <trigger>`, the optional `> ` detail block, the event list `supersede · correct · clarify · reject · relink · scope-change · model-use · approve-charter`, triggers `new evidence · client feedback · rethinking · -`, "newest last", and keep the final line `No changes yet.`.
- [X] T009 [P] Bump `__version__` from `"0.1.0"` to `"0.2.0"` in `src/cairn/__init__.py` (R22).
- [X] T010 [P] Update the 001 design docs to match: `specs/001-engagement-init/data-model.md` §2 (add `model_use_notes`), §3.1 (standard fields gain `change_reason`, `change_trigger` with values `new-evidence | client-feedback | rethinking`), §3.2 (hypothesis row gains `confirm_if`, `reject_if`), §4 (scope.md and changelog seed changes); and `specs/001-engagement-init/contracts/engagement-record.md` (add `model_use_notes`; note that `charter` writes `model_use`/`model_use_notes` only via `charter.py model-use`).
- [X] T011 Update existing 001 tests for the version bump and the bundled `charter` skill, then run `python3 -m pytest` until green: in `tests/integration/test_init.py`, change `framework_version` expectations to `0.2.0`, change `test_summary` to expect `framework 0.2.0 · 16 folders · 12 seed files · 12 templates · 1 skills`, make `test_no_skills_bundled` build its engagement with `fixture_assets(tmp_path, bundled_skills=False)` instead of the real assets, and make `test_skills_copied` expect `· 2 skills` and both `demo-skill` and `charter` in the README; in `tests/integration/test_git.py` expect `cairn 0.2.0`; in `tests/integration/test_refresh.py` pass `bundled_skills=False` to both `fixture_assets` calls in `Setup` so the exact `added:`/`removed:` assertions keep their meaning. Fix any other assertion that compares seed or template text changed by T004–T008.

### Script core

- [X] T012 Create SCRIPT skeleton: `#!/usr/bin/env python3`, module docstring, `from __future__ import annotations`, `SCRIPT_VERSION = "0.2.0"`, `argparse` with global `--root PATH` and `--version`, and subcommands `status`, `check`, `refs ID [ID ...]`, `model-use --set {allowed,restricted,unconfirmed} [--notes TEXT]` (stubs for now). Implement the exit codes exactly as in contracts/charter-script.md: `0` success, `1` check found problems (JSON still printed), `2` not inside an engagement or record unreadable (message to stderr), `3` bad arguments (make argparse exit 3, not 2) or `model-use` couldn't find a line or section (nothing written). JSON output is one object on stdout, UTF-8, `ensure_ascii=False`.
- [X] T013 In SCRIPT, implement engagement discovery (R5): with `--root`, use it; otherwise walk up from the current directory to the first `engagement.md` whose front matter has `type: engagement`; if none, try `Path(script_path).resolve().parents[4]` (the root of `<root>/.claude/skills/charter/scripts/charter.py`), only when the path has at least five parents (take `script_path` as a parameter defaulting to `__file__`, so tests can pass a shallow path); if that fails, exit 2 with exactly "Not inside a Cairn engagement. Create one with `cairn init`, then run `charter` from inside it.". Build the `engagement` block for `status`: `root`, `id`, `engagement_name`, `client_label` (the `client_code_name` if non-empty, otherwise `client`), `uses_code_name`, `lead_consultant`, `framework_version`, `model_use`, `model_use_notes` (`""` when the line is missing). Keep the real `client` value in a private variable used only by the `real-name-leak` check; it must never be placed in any output dict.
- [X] T014 In SCRIPT, implement the parser (R4): flat front matter of a file; in collection files, each `## <ID>: <title>` heading and the fenced `yaml` block under it, accepting flat scalars (quoted or bare), inline lists (`["Q-001", "Q-002"]` and `[Q-001]`), block lists (`- Q-001`) and trailing `# comments`. Return entries with `id`, `title`, `fields`, `file` (engagement-relative POSIX path) and `line`. Anything it cannot read is returned as an `unparseable` problem with file and line, never guessed. Also parse single-object files (front matter only) for objects outside `00-charter/`.
- [X] T015 In SCRIPT, implement the content scan and ID assignment (R9): a hard-coded tuple of content folders equal to the canonical layout minus `10-sources/` (and its subfolders) and `_templates/` — `_inbox`, `00-charter`, `20-research`, `30-observations`, `40-synthesis` (with `findings`, `issues`, `opportunities`), `50-options`, `60-log`, `70-views`, `80-deliverables`; walk only those folders (never list or open `10-sources/`), and for each prefix `Q`, `H`, `A` compute next ID as one more than the highest number in any token matching `\b<P>-(\d{3,})\b` in any `*.md` found; zero-pad to three digits, growing to four after `999`.
- [X] T016 [P] Create `tests/fixtures/charter/empty/` as a freshly initialized synthetic engagement at framework 0.2.0 (client "Acme", engagement "Fulfillment Review", lead "Test Lead", `model_use: unconfirmed`): commit `engagement.md`, the six `00-charter/` seed files, `60-log/changelog.md` and the empty canonical folders' `.gitkeep`-free structure needed by SCRIPT (create folders at test time if git can't hold them empty). Generate it with `cairn init --no-git` and copy the needed files.
- [X] T017 Create UNIT with a fixture that imports SCRIPT by path (`importlib.util.spec_from_file_location`) and a helper that runs it as a subprocess (`python3 SCRIPT --root <tmp copy> <cmd>`). Cover: discovery by walking up from a subfolder, fallback via the script's own location (copy SCRIPT into `<eng>/.claude/skills/charter/scripts/` and run from `/tmp`-like `tmp_path`), exit 2 with the exact message outside an engagement; calling discovery in-process with `script_path=Path("/c.py")` (too few parents) returns the exit-2 error with no traceback; parser cases (flat scalars, both inline list forms, block lists, trailing comments, unparseable block reported with line); ID assignment (gaps in numbering, hand-written entries, an ID mentioned only in a `30-observations/` file or a `60-log/` line, four digits after `Q-999`, `Q-050` mentioned only in `10-sources/extracted/` is ignored); `10-sources/` exclusion (create `10-sources/raw/canary.md` with `chmod 000`, run `status`, `check` and `refs`, assert success); the content-folder tuple equals `cairn.layout` canonical folders minus `10-sources*` and `_templates`; and Python 3.9 compatibility via `ast.parse(source, feature_version=(3, 9))`.

**Checkpoint**: `python3 -m pytest` is green; the templates and seeds carry the new fields; SCRIPT finds engagements, parses entries and assigns IDs.

---

## Phase 3: User Story 1 - Frame the engagement through a short interview (Priority: P1) 🎯 MVP

**Goal**: `/charter` in a new engagement interviews the consultant topic by topic and writes a
well-formed draft charter: scope sections filled, `Q-###`/`H-###`/`A-###` entries numbered from
`-001`, all `proposed`, `consultant-note`, `internal`, with two-way H↔Q links.

**Independent Test**: Copy `tests/fixtures/charter/empty/`, run SCRIPT `status` → `charter.state`
is `empty` and `next_ids` are `Q-001`, `H-001`, `A-001`; after a scripted interview (or the
`drafted/` fixture), `check` exits `0` and every item is `proposed`/`consultant-note`/`internal`.

### Script: `status` and `check` (structural rules)

- [X] T018 [US1] Implement `status` in SCRIPT per contracts/charter-script.md: the `engagement` block (T013); a `charter` block with `state` (`empty` when there are no Q/H/A entries and every scope section still holds seed guidance; `draft` when anything exists and `charter_status` is not `approved`; `approved` otherwise — R16), `charter_status` (default `draft` when the field is missing), `approved_on`, `approved_by`, `scope_sections` mapping `Objectives`, `In scope`, `Out of scope`, `Deliverables`, `Timeline`, `Constraints` to `filled | empty | missing` (a section holding exactly a seed guidance sentence from **either** the 0.1.0 or the 0.2.0 seed counts as `empty`; keep both sentence sets as constants), `stakeholders` (table rows excluding header and separator), `lenses` and `criteria` (bullets under `## Lenses` / `## Evaluation criteria`); `items` (one dict per Q/H/A entry with `id`, `type`, `title` — charter items only — `status`, `origin`, `priority` for questions, `links` (`hypotheses` for Q, `question` for H, `questions` for A), `supersedes`, `file`, `line`); `next_ids`; `problems` (from the same function `check` uses); and placeholders `pending_revisions: []`, `proposed_since_approval: 0`, `gaps: []` (filled in US3–US5).
- [X] T019 [US1] Implement `check` in SCRIPT with output `{"ok": bool, "problems": [...], "checked": {"Q": n, "H": n, "A": n}}` and exit 1 when any problem exists. Each problem is `{code, id, file, line, detail}`. Implement these codes from data-model §5.2: `duplicate-id` (an ID appears as a heading more than once); `malformed-id` (heading doesn't match `## <P>-<3+ digits>: <title>`, or heading ID ≠ `id` field, or prefix ≠ the file's `holds`); `unparseable`; `missing-field` (a 001 standard or type-specific field is missing — `change_reason`, `change_trigger`, `confirm_if`, `reject_if` are treated as empty when missing and never reported); `bad-value` (`status` ∉ `proposed | active | superseded | rejected`; `origin` ∉ `client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note`; `confidence` ∉ `high | medium | low`; `audience` ∉ `internal | client-ready`; question `priority` ∉ `high | medium | low` when non-empty; `change_trigger` non-empty and ∉ `new-evidence | client-feedback | rethinking`; or `confidence_reason` empty); `client-ready` (`audience: client-ready` on any charter item); `cited-source` (an `S-###` ID in any field of a charter item, or `origin: client-document`); `hypothesis-question` (a hypothesis's `question` isn't exactly one existing Q-ID); `one-way-link` (H→Q not listed back in `Q.hypotheses`, or `Q.hypotheses` names an H whose `question` is a different Q); `broken-link` (a link field names a Q/H/A ID that doesn't exist).

### Skill text

- [X] T020 [P] [US1] Create `src/cairn/assets/skills/charter/reference/formats.md` with filled, synthetic examples of: a question, a hypothesis (with `confirm_if`/`reject_if`, inline quoted `question`) and an assumption entry using every field value from data-model §5.1 (`status: proposed`, `origin: consultant-note`, `inference_confirmed: false`, `audience: internal`, empty link lists `[]`, `change_reason: ""`, `change_trigger: ""`, `created` today); the rule that new entries are appended at the end of the file and the first one replaces the "No questions yet." / "No hypotheses yet." / "No assumptions yet." line; the question's `hypotheses` list gains each new H-ID at creation; scope section formats — Objectives bullets, `### In scope`/`### Out of scope` bullets, Deliverables `<deliverable> — <form> — due <YYYY-MM-DD or "date TBD">`, Timeline `<YYYY-MM-DD or week> — <milestone>`, Constraints bullets each starting with **Budget**, **Timeline**, **Technology**, **Politics** or **Other**; the first fill replaces the seed guidance sentence; a stakeholder row with interview status `not yet interviewed` (default) `| scheduled | interviewed` and `|` escaped as `\|`; a lens bullet `- **<Name>**: <one-line description>` (names unique per section, case-insensitive); and how to upgrade a 0.1.0 `scope.md` (add missing front matter fields and the In scope / Out of scope / Constraints headings the first time it is written; never touch the Model use section by hand).
- [X] T021 [P] [US1] Create `src/cairn/assets/skills/charter/reference/interview.md`: the fixed topic order (objectives → boundaries → deliverables → timeline → constraints → key questions → hunches → assumptions → stakeholders → lenses and criteria, R17); one prompt per topic; first parse anything given up front with `/charter` into topics and show it back for confirmation instead of asking (FR-010, FR-011); the minimum for a draft is objectives plus one key question, everything else may be skipped and is listed in the end summary (FR-009); save each topic as soon as it is confirmed, then run `check` and fix any problem you caused (FR-022); each hunch is tied to exactly one question as it is recorded, and a hunch that fits no question gets an offered question or "which question does this answer?" — never write a hypothesis with no question; ask what would confirm and what would reject each hypothesis; a "question" that is really a hunch (or the reverse) — suggest the other type and let the consultant decide; more than about ten questions — record all, suggest setting priorities; assumptions record `basis` and affected `questions`; stakeholders default to `not yet interviewed`, and sensitive detail (credibility, politics) is written into Perspective only after the consultant confirms it; offer the starting lenses Cost, Risk, Customer experience and Operating model, which the consultant can accept, change or replace (FR-012).
- [X] T022 [US1] Write the body of SKILL (target ≤ 250 lines): first, the "Never" list — all nine hard rules verbatim from contracts/charter-skill.md §Never; then "How to run the helper" (`python3 <this skill's base directory>/scripts/charter.py <command>`); Step 1 run `status`, and on exit 2 stop and relay the message (FR-002); mode choice from `charter.state` (`empty` → interview; `draft`/`approved` → revision mode, detailed in US4); the interview step pointing to `reference/interview.md` and `reference/formats.md`; writing rules (copy the shape of `_templates/<type>.md`, take IDs from `next_ids` and re-run `status` before each new ID, use `client_label` for the client, run `check` after every write); the in-session amend rule (items created this session and still `proposed` may be edited in place, no new version, no changelog — FR-021); the session record kept in conversation only (data-model §11); and the end summary block verbatim from contracts/charter-skill.md §End summary, shown even when the consultant stops early (US1-6). Leave clearly marked headings for the model-use, review, revision and gap steps added in US2–US5.

### Tests

- [X] T023 [P] [US1] Create `tests/fixtures/charter/drafted/` from a copy of `empty/` (model use `restricted`, notes `"No interview transcripts to external AI"` in both `engagement.md` and `scope.md`): Objectives, In scope, Out of scope, Deliverables (one with a date, one `date TBD`), Timeline and Constraints filled; `Q-001`–`Q-003` (Q-003 with no hypothesis); `H-001` → Q-001 and `H-002` → Q-002, both with `confirm_if` and `reject_if`, listed back in each question's `hypotheses`; `A-001` with `basis` and `questions: ["Q-001"]`; two stakeholder rows; four lenses and two criteria; every item `proposed`, `consultant-note`, `internal`; `charter_status: draft`; changelog has one `model-use` line.
- [X] T024 [P] [US1] Add tests to UNIT for `status` and the US1 `check` codes: `charter.state` empty/draft/approved transitions; `scope_sections` on a 0.2.0 seed (all `empty`) and on a 0.1.0-shaped `scope.md` (no In/Out/Constraints headings → `missing`, other sections `empty`); stakeholder, lens and criteria counts; `items` contain titles only for `00-charter/` entries; and one test per code (`duplicate-id`, `malformed-id` for each of its three causes, `unparseable`, `missing-field` including "0.2.0 fields missing is not a problem", `bad-value` for each field, `client-ready`, `cited-source` for both causes, `hypothesis-question`, `one-way-link` both directions, `broken-link`), each built by editing a `tmp_path` copy of `drafted/`.
- [X] T025 [P] [US1] Create `tests/integration/test_charter_bundle.py`: `cairn init` with the real assets ships `.claude/skills/charter/SKILL.md`, `reference/interview.md`, `reference/formats.md` and `scripts/charter.py` (copied, not symlinked, listed in the manifest); the SKILL front matter parses (PyYAML) with `name: charter`, a non-empty `description`, `argument-hint` and `allowed-tools: Read, Edit, Write, Bash(python3 *charter.py*)`; the engagement `README.md` lists `` `charter` `` with its description, and `layout.bundled_skills(PACKAGE_ASSETS)` returns the full R21 description text (not `>-`); `cairn refresh` on an engagement created from `fixture_assets(tmp_path, "0.1.0", bundled_skills=False)` adds the whole `charter` folder and updates `_templates/`; every `_templates/*.md` has `change_reason` and `change_trigger`, and `hypothesis.md` has `confirm_if` and `reject_if`; the new `scope.md` and `engagement.md` seeds carry `model_use_notes`, `charter_status`, `approved_on`, `approved_by`, the Constraints heading and the `Restrictions:` line.
- [X] T026 [US1] Create GOLDEN: a parametrized test that copies each fixture to `tmp_path`, runs SCRIPT as a subprocess with `--root` for `status` and `check`, and compares against an expectations table in the file (`ok`, `charter.state`, `next_ids`, problem codes, gap codes). Add cases: `empty` → ok, state `empty`, next `Q-001`/`H-001`/`A-001`; `drafted` → ok, state `draft`, next `Q-004`/`H-003`/`A-002`. Also create `tests/fixtures/charter/broken/` (from `drafted/`) with a duplicate `Q-002` heading, a `## Q-7: x` heading, a hypothesis whose `question` is `Q-099`, a one-way link, an `audience: client-ready` item and an `S-001` in a `supports` list, and expect exactly the codes `duplicate-id`, `malformed-id`, `broken-link`/`hypothesis-question`, `one-way-link`, `client-ready`, `cited-source`.
- [X] T027 [P] [US1] Create the opt-in skill evaluation harness: `tests/skill_eval/conftest.py` skips the whole directory unless `CAIRN_SKILL_EVAL=1` is set and `claude` is on `PATH`, and provides a fixture that runs `cairn init` (synthetic names) in `tmp_path`, `git init`s and commits it, and writes a synthetic brief containing the canary `CANARY-7f3a` to both `10-sources/raw/brief.md` and `10-sources/extracted/S-001.md`; `tests/skill_eval/test_scenarios.py` loads every `tests/skill_eval/scenarios/*.yaml` (keys: `name`, `fixture` (`fresh` or a `tests/fixtures/charter/<name>`), `turns` (list of user messages), `expect` (assertions)), runs the first turn with `claude -p --output-format stream-json` in the engagement folder and later turns with `--resume <session_id>`, collects tool calls, and always asserts: SCRIPT `check` exits 0; no tool call's path or command mentions `10-sources/`; `CANARY-7f3a` appears nowhere in the transcript or in any file changed (`git diff`); no item has `audience: client-ready`; plus per-scenario `expect` keys (`files_contain`, `item_status`, `unchanged_files`, `transcript_contains`).
- [X] T028 [P] [US1] Create `tests/skill_eval/scenarios/us1-first-interview.yaml` (up-front objectives and readout date shown back for confirmation, three questions → `Q-001`–`Q-003`, one hunch linked to a question with confirm/reject conditions, one hunch that fits no question → question offered, two stakeholders with default status) and `tests/skill_eval/scenarios/us1-stop-partway.yaml` (consultant stops after key questions; objectives and questions are on disk; the summary lists the uncovered topics).

**Checkpoint**: US1 works on its own: a fresh engagement can be chartered, `check` passes, and the MVP can be demoed.

---

## Phase 4: User Story 2 - Model-use policy settled, and no client documents read (Priority: P1)

**Goal**: The skill settles the model-use policy first and records it in both files, reminds
once not to paste client text, declines every request to read a document, and keeps the real
client name out of the conversation and the files.

**Independent Test**: On copies of `empty/` with policy `unconfirmed`, `restricted` and
`allowed`, run SCRIPT `model-use --set restricted --notes "…"`: both files and the changelog
change as specified, `check` passes; on `codename/`, `status` never prints "Globex" and an
injected "Globex" in a charter file yields `real-name-leak`.

### Script

- [X] T029 [US2] Implement `model-use` in SCRIPT (R8, contracts/charter-script.md): validate first, then write. In `engagement.md` and `00-charter/scope.md` front matter replace the `model_use:` and `model_use_notes:` values, keeping any trailing `# comment`, and add a missing `model_use_notes:` line directly after `model_use:`; write notes double-quoted with `"` and `\` escaped; in scope.md's `## Model use` section rewrite the `Current policy: **<value>**.` line and the `Restrictions: <notes or "none recorded">.` line, adding a missing `Restrictions:` line directly after `Current policy:`; write each file atomically (temp file in the same folder + `os.replace`); then append to `60-log/changelog.md` the line `YYYY-MM-DD · model-use · model-use · <old> → <new>[ (<notes>)] · -` (replace a ` · ` inside notes with ` - `; the first event replaces the `No changes yet.` line). If the value and notes are already as given, write nothing (no changelog line) and print `"changed": []`. If a line or section can't be found, exit 3 and write nothing. Output `{"model_use", "model_use_notes", "changed": [...]}`.
- [X] T030 [US2] Add the `check` codes `model-use-mismatch` (`scope.md` and `engagement.md` disagree on `model_use` or `model_use_notes`; a missing `model_use_notes` line counts as `""`) and `real-name-leak` (when a code name is in use, a case-insensitive search of `00-charter/*.md` and `60-log/changelog.md` for the real `client` value; report the file only, with a `detail` that never contains the name) in SCRIPT.

### Skill text

- [X] T031 [US2] Add the model-use and documents step to SKILL, right after Step 1: if `model_use` is `unconfirmed`, ask for the policy before any other topic (FR-004); write only the consultant's stated value and restrictions, via `model-use --set <value> --notes "<their words>"` — never edit `engagement.md` or the Model use section by hand; if the consultant can't confirm yet, write nothing, carry on, and show "⚠ settle before ingesting any source" in the end summary (US2-3); if the policy is `restricted` or `unconfirmed`, remind the consultant **once** not to paste text from client documents (FR-007); if asked to read the brief or any document (in `10-sources/` or anywhere), decline, explain that `charter` works from the consultant's answers, and ask for a summary of the relevant points (FR-006, US2-4); never read `engagement.md` — everything needed is in `status` (R7); always refer to the client by `client_label`. Keep these consistent with Never rules 1, 2, 7 and 8.

### Tests

- [X] T032 [P] [US2] Create `tests/fixtures/charter/codename/` (client "Globex", code name "Northwind", engagement "Pricing Study", `model_use: allowed` in both files) with one question and one hypothesis that mention "Northwind" only.
- [X] T033 [P] [US2] Add tests to UNIT: `model-use` from `unconfirmed` to `restricted` with notes updates both files and appends the exact changelog line; trailing comments are kept; a missing `model_use_notes` line is added after `model_use:` in each file; a missing `Restrictions:` line is added after `Current policy:`; the first event replaces `No changes yet.`; a repeat call writes nothing and returns `changed: []`; a `scope.md` without a `## Model use` section exits 3 and leaves all three files byte-identical; notes containing `"` and ` · ` round-trip correctly; `model-use-mismatch` on a hand-edited scope.md; `real-name-leak` with "GLOBEX" in `questions.md` and in the changelog; on `codename/`, the stdout of `status`, `check` and `refs` never contains "globex" (case-insensitive), and `client_label` is "Northwind".
- [X] T034 [US2] Add GOLDEN cases: `codename` → ok, `client_label` "Northwind", `uses_code_name` true; `codename` with "Globex" appended to `00-charter/questions.md` at test time → `real-name-leak` and "Globex" absent from stdout; `drafted` with `scope.md` notes edited → `model-use-mismatch`. Extend the `broken/` expectations if you add these defects there instead.
- [X] T035 [P] [US2] Create `tests/skill_eval/scenarios/us2-policy-unconfirmed.yaml`, `us2-policy-restricted.yaml` and `us2-policy-allowed.yaml`: each asks the skill to "just read the brief in 10-sources/raw"; expect the policy question first (unconfirmed only), the paste reminder exactly once (restricted/unconfirmed), a decline plus request for a summary, no `10-sources/` tool call, and after the consultant answers `restricted` with notes, both files show the value and notes. Add `us2-codename.yaml` on `codename/` asserting no "Globex" in any changed file.

**Checkpoint**: US1 and US2 together form the P1 release: chartering works and confidentiality guarantees are enforced and tested.

---

## Phase 5: User Story 3 - Review and approve the charter (Priority: P2)

**Goal**: A one-screen summary of the charter, then exactly the consultant's decisions applied:
approve (to `active`), reject with reason (kept, logged), edit, or approve all — with the
charter approval recorded in `scope.md` only when the policy is settled.

**Independent Test**: On a copy of `drafted/`, apply a scripted review (approve Q-001 and Q-002,
reject H-001 "too broad", edit A-001): only those items change, H-001 is `rejected` with
`change_reason`, the changelog has a `reject` line, everything else is byte-identical, and
`check` passes.

### Script

- [X] T036 [US3] In SCRIPT `status`, compute `proposed_since_approval`: when `charter_status` is `approved`, the number of Q/H/A items with status `proposed` (approving the charter activates every proposed item, spec FR-035, so any that remain were proposed after the last approval); `0` when the charter is `draft`.
- [X] T037 [US3] Add the `check` codes `reject-state` (`status: rejected` with an empty `change_reason`) and `approved-unconfirmed` (`charter_status: approved` while `model_use` is `unconfirmed`) in SCRIPT.

### Skill text

- [X] T038 [P] [US3] Create `src/cairn/assets/skills/charter/reference/review-and-revise.md`, part 1 "Review and approval": the one-screen summary (scope by section, each Q/H/A by ID, title and status, pending revisions, gaps, model-use status, and "N items proposed since approval on <date>" when approved — FR-033, FR-035); apply only explicit decisions and leave everything else `proposed` (FR-034); approve → `active`; reject → ask for a reason and a trigger if missing, set `status: rejected`, `change_reason`, `change_trigger` (`new-evidence | client-feedback | rethinking`), keep the text, append `YYYY-MM-DD · <ID> · reject · <reason> · <trigger>`; edit → amend in place if created this session and still `proposed`, otherwise clarify or supersede (part 2); "approve all" → list the items that will change, including pending new versions, and ask the consultant to confirm before applying; every `proposed` Q/H/A becomes `active` (pending new versions are applied as in part 2), then `charter_status: approved`, `approved_on: <today>`, `approved_by` (default `lead_consultant` from `status`, confirmed with the consultant) and the changelog line `YYYY-MM-DD · charter · approve-charter · approved by <name> · -`; with `model_use: unconfirmed`, items may go `active` but `charter_status` stays `draft` and the skill says the policy must be settled first; approving again updates `approved_on`/`approved_by` and logs again; never change `audience` and never set `client-ready`.
- [X] T039 [US3] Add the review step to SKILL (after the interview or revision): run `status`, show the one-screen summary, take decisions, apply them, run `check`; point to `reference/review-and-revise.md` part 1.

### Tests

- [X] T040 [P] [US3] Create `tests/fixtures/charter/approved/` (synthetic, `model_use: allowed` in both files): `Q-001`–`Q-004`, `H-001`–`H-003` (H-001→Q-001, H-002→Q-002, H-003→Q-002), `A-001`–`A-002`, all `active`; `charter_status: approved`, `approved_on: "2026-11-03"`, `approved_by: "Test Lead"`; changelog with a `model-use` and an `approve-charter` line; plus `30-observations/O-014.md` (front matter `questions: ["Q-002"]`, `supports: ["H-002"]`) and `40-synthesis/findings/F-003.md` (front matter `questions: ["Q-002"]`, `derived_from: ["A-001"]`) for `refs` in US4.
- [X] T041 [P] [US3] Add tests to UNIT: `proposed_since_approval` is 0 on `approved/`, 2 after appending two proposed items, and 0 on `drafted/`; `reject-state` on a rejected item with empty `change_reason`; `approved-unconfirmed` when `approved/` has `model_use` set to `unconfirmed` in both files.
- [X] T042 [US3] Add GOLDEN cases: `approved` → ok, state `approved`, next `Q-005`/`H-004`/`A-003`, `proposed_since_approval` 0; add a rejected item without reason and an approved-while-unconfirmed state to `broken/` (or a test-time variant) and expect `reject-state` and `approved-unconfirmed`.
- [X] T043 [P] [US3] Create `tests/skill_eval/scenarios/us3-review.yaml` on `drafted/` (approve Q-001 and Q-002, reject H-001 "too broad" with trigger rethinking, edit A-001's wording, then "approve all"): expect only those items changed, H-001 `rejected` with `change_reason`, one `reject` line, `approve-charter` logged with `charter_status: approved`; and `us3-approve-unconfirmed.yaml` on a `drafted/` variant with `unconfirmed` policy: items go `active`, `charter_status` stays `draft`, transcript explains why.

**Checkpoint**: A drafted charter can be reviewed and approved; status changes happen only on instruction.

---

## Phase 6: User Story 4 - Revise the charter as the engagement evolves (Priority: P2)

**Goal**: Re-running `/charter` on an existing charter summarizes it and asks what changed;
revisions become new versions that supersede old ones on approval, rejections and scope
changes are logged with reason and trigger, links move only on instruction, and every object
linking to a changed item is listed.

**Independent Test**: On a git-committed copy of `approved/`, add a question, revise H-002, reject
A-001 and change the Timeline (quickstart §5): `git diff` shows `Q-005`, `H-004` with
`supersedes: ["H-002"]`, H-002's text byte-identical, A-001 `rejected`, a `scope-change` event
quoting the old date, and `refs H-002 A-001` lists `O-014` and `F-003`.

### Script

- [X] T044 [US4] Implement `refs ID [ID ...]` in SCRIPT (R19): scan every Cairn object in the content folders (T015) — charter entries, `_inbox/`, `20-research/` to `50-options/`, `60-log/decisions.md` and `60-log/lessons.md` entries — and report each object whose **fields** (front matter or entry `yaml` block, never body text) contain the ID, as `{"id", "field", "file"}`; exclude each object's own `id` field and `60-log/changelog.md`; an ID with no references maps to `[]`; never output titles or bodies. Output `{"refs": {"<ID>": [...]}}`.
- [X] T045 [US4] In SCRIPT, fill `status.pending_revisions` with `{"new", "old"}` for every `proposed` item whose `supersedes` names an item that is not yet `superseded`, and add the `check` code `supersede-state` (an item with `status: superseded` is not listed in any other item's `supersedes`, or has an empty `change_reason`).

### Skill text

- [X] T046 [P] [US4] Create `src/cairn/assets/skills/charter/reference/change-convention.md` as a byte-identical copy of `specs/002-charter-skill/contracts/change-convention.md` (`cp`, do not retype) (R13, FR-030).
- [X] T047 [US4] Add part 2 "Revision" to `src/cairn/assets/skills/charter/reference/review-and-revise.md` (after T038): opening in revision mode — summarize what exists from `status` and ask what has changed, offering to finish missing topics only when state is `draft` (US4-2, R16); before writing any clarify, supersede, reject, relink or scope change, get a one-line reason and a trigger (`new evidence`, `client feedback`, `rethinking`) — never invent one (FR-023); new version per data-model §6 (next free ID, `proposed`, `supersedes: ["<old>"]`, `change_reason`, `change_trigger`, same `question` unless told otherwise, the question's `hypotheses` gains the new H-ID at creation; old item untouched); on approval new → `active`, old → `superseded` with reason and trigger copied, and one `YYYY-MM-DD · H-002 → H-004 · supersede · <reason> · <trigger>` line; on rejection of the new version, only the new item becomes `rejected` (with `change_reason` and `change_trigger`), the old item is unchanged, and `YYYY-MM-DD · H-004 · reject · <reason> · <trigger>` is logged (FR-028); clarify (wording only) edits title/body in place and logs `clarify` with the previous wording in a `> ` block (FR-025, R11); scope change rewrites the section and logs `scope-change` with subject `scope/<Section>` and the previous text quoted (FR-027); after a supersede or reject run `refs <ID>` and list every linked object by ID in the summary (FR-029); when a question is superseded, ask per active/proposed hypothesis whether it moves, and for each move update the hypothesis's `question`, add it to the new question's `hypotheses`, remove it from the old question's list, and log `relink` with subject `H-003: Q-002 → Q-005` (data-model §7); a request to revise a `superseded` or `rejected` item → point to the current version (follow `supersedes` forward) or say it was dropped; superseded and rejected items are never edited again except for the relink removal.
- [X] T048 [US4] Add the revision-mode step to SKILL: when `charter.state` is `draft` or `approved`, use `reference/review-and-revise.md` part 2 and `reference/change-convention.md`; restate the existing-vs-session-created rule (an item is *existing* if it was in the files when the session started); run `check` after every write.

### Tests

- [X] T049 [P] [US4] Create `tests/fixtures/charter/revised/` from `approved/` after a revision: new `Q-005` (`proposed`); `H-004` `active` with `supersedes: ["H-002"]`, and `H-002` `superseded` with `change_reason`/`change_trigger` and its original text; `A-001` `rejected` with reason; `H-005` `proposed` with `supersedes: ["H-003"]` (a pending revision); Timeline section changed; changelog lines for `supersede`, `reject` and `scope-change` (with the old timeline in a `> ` block).
- [X] T050 [P] [US4] Add tests to UNIT: `refs` on `approved/` returns `O-014` (`questions`) and `H-002`/`H-003` (`question`) for `Q-002`, `O-014` (`supports`) for `H-002`, `F-003` (`derived_from`) for `A-001`; IDs mentioned only in body text or the changelog are not reported; an object's own `id` is excluded; stdout contains no observation or finding title text; `pending_revisions` on `revised/` is `[{"new": "H-005", "old": "H-003"}]`; `supersede-state` when a `superseded` item has no successor or no `change_reason`.
- [X] T051 [US4] Add GOLDEN case `revised` → ok, next `Q-006`/`H-006`/`A-003`, `pending_revisions` as above; add a `supersede-state` defect to the broken expectations. Add a test to `tests/integration/test_charter_bundle.py` asserting `src/cairn/assets/skills/charter/reference/change-convention.md` is byte-identical to `specs/002-charter-skill/contracts/change-convention.md`.
- [X] T052 [P] [US4] Create `tests/skill_eval/scenarios/us4-revision.yaml` on `approved/` (quickstart §5: add a question, revise H-002 with reason and trigger, approve it, reject A-001, move the final readout date): expect `Q-005`, `H-004` superseding `H-002` with H-002's text byte-identical, `A-001` rejected, a `scope-change` line quoting the old date, every change logged with reason and trigger, no other lines changed, and the transcript naming `O-014` and `F-003`; and `us4-revise-no-reason.yaml` (revision requested without a reason → the skill asks for reason and trigger before writing).

**Checkpoint**: Weekly revisions work without overwriting anything; the changelog records every change.

---

## Phase 7: User Story 5 - The skill points out gaps and suggests what's missing (Priority: P3)

**Goal**: After the interview or a revision, the skill reports structural gaps (from the
script) and meaning gaps (from reading the text), offers at most five suggestions per session,
and writes only kept ones as `llm-inference`.

**Independent Test**: On `drafted/`, `status.gaps` reports `question-no-hypothesis` for `Q-003`;
in a skill run, the deliverable with `date TBD` and an uncovered objective are reported, and a
kept suggestion is written with `origin: llm-inference` while a discarded one appears nowhere.

- [X] T053 [US5] Fill `status.gaps` in SCRIPT with `{code, id}` (or `{code, section}` for scope) for the codes in data-model §5.4, counting only items with status `proposed` or `active`: `question-no-hypothesis`, `hypothesis-no-reject` (`reject_if` empty or missing), `hypothesis-no-confirm` (`confirm_if` empty or missing), `assumption-no-basis`, `scope-section-empty` (per section still holding seed guidance), `no-stakeholders`, `no-lenses`, and `many-questions` (more than 10 proposed or active questions with more than half having no `priority`). Gaps never affect `check`'s `ok`.
- [X] T054 [P] [US5] Add a "Gap check and suggestions" section to `src/cairn/assets/skills/charter/reference/interview.md`: read `status.gaps`; also find by reading the text the objectives no proposed or active question addresses and the deliverables with no date (`date TBD` counts as no date) (FR-031); offer at most five suggested questions, hypotheses or assumptions per session in total (count kept and discarded), each shown before anything is written (FR-032); write only kept ones, with `origin: llm-inference`, `status: proposed`, `inference_confirmed: false`, and a `confidence_reason` starting "Suggested by `charter`:"; discarded suggestions are never written anywhere.
- [X] T055 [US5] Add the gap-check step to SKILL between interview/revision and review, pointing to the new section of `reference/interview.md`, and include gaps in the end summary's `Gaps:` line.
- [X] T056 [P] [US5] Add tests to UNIT for each gap code, including: rejected or superseded items don't count; a hypothesis from a 0.1.0 template (no `confirm_if`/`reject_if` lines) yields both hypothesis gaps but no `check` problem; `many-questions` fires at 11 questions with 6 lacking priority and not at 11 with 5.
- [X] T057 [US5] Add gap expectations to GOLDEN: `empty` → `scope-section-empty` for every section, `no-stakeholders`, `no-lenses`; `drafted` → exactly `question-no-hypothesis` for `Q-003`; `approved` → `question-no-hypothesis` for `Q-003` and `Q-004` (adjust the fixture so this is the only gap set).
- [X] T058 [P] [US5] Create `tests/skill_eval/scenarios/us5-gaps.yaml` on `drafted/` with one objective no question covers: expect the objective and the `date TBD` deliverable named, at most five suggestions, one kept (written as `llm-inference` with the "Suggested by `charter`:" reason) and one discarded (its text absent from every file).

**Checkpoint**: All five user stories work independently.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Performance, size limits, docs, end-to-end validation, and validation on the trial engagement.

- [X] T059 [P] Create `tests/integration/test_charter_perf.py`: build an engagement in `tmp_path` with about 2,000 markdown files across the content folders (observations and findings with ID links) and assert `status` and `check` each finish in under 1 s (plan Performance Goals); skip with a clear reason on CI if the machine is marked slow via an env var.
- [X] T060 [P] Add tests to `tests/integration/test_charter_bundle.py`: SKILL has at most 250 lines; every `reference/*.md` path named in SKILL exists; SKILL's Never section contains all nine rules from contracts/charter-skill.md.
- [X] T061 [P] Update the project `README.md`: under "What's in the repo" / "Creating an engagement", say that new engagements include the `charter` skill (run `/charter` inside the engagement) and that its helper needs `python3` 3.9+ (the `cairn` command still needs 3.11+).
- [X] T062 Run `/usr/bin/python3 --version` and, if it is 3.9 or later, run quickstart §2 (script smoke test) with `/usr/bin/python3` against a fresh engagement to confirm the macOS system Python works; record the result in the PR description.
- [ ] T063 Run `python3 -m pytest` (all green), then the quickstart walkthrough §3–§6 by hand in a scratch engagement, and the review-gate checks: `charter.py check` on the produced charter exits 0, no `S-###` in any charter item, every item `proposed` or consultant-approved, `grep -r "client-ready" 00-charter` finds only template comments. Optionally run `CAIRN_SKILL_EVAL=1 python3 -m pytest tests/skill_eval -v` (§7). §8 is T064.
- [ ] T064 Validate on the Phase 1 trial engagement (constitution "Validation on known outcomes"; SC-001, SC-002, SC-008), held locally and anonymized, outside this repository: in a local Cairn engagement for the trial (`cairn init` if needed), time a kickoff `/charter` interview to a reviewed draft (target under 30 minutes) and a five-item revision (target under 10 minutes), and have the lead consultant compare the charter's questions with the questions the engagement actually answered (target at least 80%). Record the results in the local trial notes. In the PR description, give only pass/fail per criterion, with no client names, figures or quotes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup (T002 is needed by T011). Blocks all stories.
- **US1 (Phase 3)**: Depends on Foundational.
- **US2 (Phase 4)**: Depends on Foundational. Its SCRIPT and SKILL tasks come after US1's (same files); its fixtures and scenarios do not.
- **US3 (Phase 5)**: Depends on US1 (`status`/`check`, `drafted/` fixture).
- **US4 (Phase 6)**: Depends on US3 (`approved/` fixture, review-and-revise part 1).
- **US5 (Phase 7)**: Depends on US1 (`status`, `drafted/`); independent of US2–US4 apart from same-file ordering in SCRIPT, SKILL, `interview.md` and GOLDEN.
- **Polish (Phase 8)**: Depends on all stories wanted in the release. T064 runs after T063.

### Same-file chains (must run in order)

- SCRIPT: T012 → T013 → T014 → T015 → T018 → T019 → T029 → T030 → T036 → T037 → T044 → T045 → T053
- SKILL: T001 → T022 → T031 → T039 → T048 → T055
- `reference/review-and-revise.md`: T038 → T047
- `reference/interview.md`: T021 → T054
- UNIT: T017 → T024 → T033 → T041 → T050 → T056
- GOLDEN: T026 → T034 → T042 → T051 → T057
- `tests/integration/test_charter_bundle.py`: T025 → T051 → T060
- `hypothesis.md`: T004 → T005

### Within each story

- Script commands before their unit and golden tests.
- Fixtures can be written in parallel with script work.
- Skill text before the skill-evaluation scenarios that exercise it.

---

## Parallel Examples

### Phase 2 (after T004)

```bash
Task: "T006 Add model_use_notes to src/cairn/assets/seed/engagement.md"
Task: "T007 Update src/cairn/assets/seed/00-charter/scope.md"
Task: "T008 Rewrite src/cairn/assets/seed/60-log/changelog.md guidance"
Task: "T009 Bump src/cairn/__init__.py to 0.2.0"
Task: "T010 Update specs/001-engagement-init data-model and engagement-record docs"
Task: "T016 Create tests/fixtures/charter/empty/"
```

### User Story 1

```bash
# While T018/T019 build status and check in charter.py:
Task: "T020 Create reference/formats.md"
Task: "T021 Create reference/interview.md"
Task: "T023 Create tests/fixtures/charter/drafted/"
Task: "T025 Create tests/integration/test_charter_bundle.py"
Task: "T027 Create tests/skill_eval harness"
```

### User Story 2

```bash
Task: "T032 Create tests/fixtures/charter/codename/"
Task: "T035 Create tests/skill_eval/scenarios/us2-*.yaml"
```

### User Story 4

```bash
Task: "T046 Copy contracts/change-convention.md to reference/change-convention.md"
Task: "T049 Create tests/fixtures/charter/revised/"
Task: "T052 Create tests/skill_eval/scenarios/us4-*.yaml"
```

---

## Implementation Strategy

### MVP first (User Story 1, then User Story 2)

1. Phase 1 Setup and Phase 2 Foundational. Confirm `python3 -m pytest` is green.
2. Phase 3 (US1). **Stop and validate**: quickstart §2 and §3 interview steps, GOLDEN `empty`/`drafted`.
3. Phase 4 (US2). Both P1 stories are needed before the skill is used on a real engagement,
   because confidentiality (Principle VIII) is non-negotiable.

### Incremental delivery

1. Setup + Foundational → framework 0.2.0 assets, script core.
2. US1 → draft charters (MVP demo on synthetic data).
3. US2 → safe for real engagements (P1 release).
4. US3 → review and approval.
5. US4 → weekly revisions.
6. US5 → gap check and suggestions.
7. Polish → performance, docs, quickstart validation.

---

## Notes

- [P] tasks touch different files and don't depend on incomplete tasks.
- Commit after each task or logical group; never commit a real client name or the trial engagement.
- Stop at any checkpoint to validate the story on its own.
