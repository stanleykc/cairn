---

description: "Task list for Charter-Relevant Observations (006-charter-relevant-observations)"
---

# Tasks: Charter-Relevant Observations

**Input**: Design documents from `/specs/006-charter-relevant-observations/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R11), data-model.md, contracts/
(observe-script.md, extract-observations-skill.md, observation-file.md), quickstart.md

**Tests**: Included. The plan (Implementation Order step 2) says unit tests are written
first for every script change, and research R10 lists the unit tests, golden fixtures and
skill-eval scenarios. SC-001, SC-002 and SC-006 are checked by skill evals; SC-003 to SC-005
are the consultant's manual check (T046).

**Organization**: Tasks are grouped by user story. The script, `SKILL.md`,
`writing-observations.md` and the unit test file are edited by several stories, so tasks
that touch them run in story order (see "Same-file chains").

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Every task names the exact file(s) it touches

## Path Conventions

This feature changes the existing `extract-observations` skill bundle of the `cairn`
package (plan.md → Project Structure). Shorthand used below:

- **SCRIPT** = `src/cairn/assets/skills/extract-observations/scripts/observe.py`
- **SKILL** = `src/cairn/assets/skills/extract-observations/SKILL.md`
- **WRITING** = `src/cairn/assets/skills/extract-observations/reference/writing-observations.md`
- **TEMPLATE** = `src/cairn/assets/templates/observation.md`
- **UNIT** = `tests/unit/test_observe_script.py`
- **GOLDEN** = `tests/integration/test_observe_golden.py`
- **BUNDLE** = `tests/integration/test_observe_bundle.py`
- **FIX** = `tests/fixtures/observe/golden/`
- **EVAL** = `tests/skill_eval/scenarios/extract-observations/`
- **HARNESS** = `tests/skill_eval/conftest.py` and `tests/skill_eval/test_scenarios.py`

## Rules every task must respect

- SCRIPT stays Python **3.9+**, standard library only (`from __future__ import annotations`,
  no `match`, no runtime `X | Y`, never imports `cairn`). UNIT already checks this with
  `ast.parse(..., feature_version=(3, 9))`.
- The assistant judges relevance; the script checks only what is mechanical (research R1).
  Do not add keyword or similarity scoring to SCRIPT.
- Passed-over material is never written anywhere: no file, log line, `progress.json` key or
  drafts-file key (FR-010). It exists only in the session summary.
- No migration: do not edit or backfill observations that already exist in an engagement
  or in `FIX/us4/_inbox/` (spec Assumptions, research R3).
- All fixtures and examples are synthetic: client "Acme", code name "Northwind",
  engagement "Fulfillment Review", lead "Test Lead" (constitution VIII). Nothing from the
  trial engagement enters the repository. Hand-built sources follow the 005
  "Hand-built source rule" (`specs/005-extract-observations/tasks.md` § Rules).
- Usable question = status `active` or `proposed` (data-model §3).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Version bump. There is no new project structure; everything lives in the
existing skill bundle.

- [ ] T001 Bump `__version__` from `"0.5.0"` to `"0.6.0"` in `src/cairn/__init__.py` (plan: template change) and `SCRIPT_VERSION` from `"0.5.0"` to `"0.6.0"` in SCRIPT (its contract changes). Leave `SCRIPT_VERSION` in `src/cairn/assets/skills/ingest/scripts/ingest.py` and `src/cairn/assets/skills/charter/scripts/charter.py` unchanged.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The new `relevance` field in the template and the script's field lists, shared
charter helpers, the eval-harness keys the new scenarios need, and the existing tests the
version bump and new field break.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. After T003,
the golden expected files fail until T014, T015 and T031.

- [ ] T002 [P] In TEMPLATE, insert directly after the `questions:` line: `relevance: ""             # one line: how the claim bears on each tagged question, "Q-###: …"`, and change the `questions` comment to `# Q-IDs; at least one` (data-model §1). Keep the comment column aligned with the neighbouring lines.
- [ ] T003 In SCRIPT, add `"relevance"` to `SKILL_FIELDS` immediately after `"questions"` and to `DRAFT_REQUIRED`. Do **not** add it to `STORED_REQUIRED` (research R3). Remove `"question-retired"` from `WARNING_CODES` (data-model §6). Make `render_observation` write `relevance` as a double-quoted one-line string, using the same escaping as `confidence_reason`.
- [ ] T004 In SCRIPT, add helper `usable_questions(eng) -> list` returning the sorted IDs from `load_questions()` whose status is `active` or `proposed`, and helper `charter_status(eng) -> str` reading the `charter_status` key from the front matter of `00-charter/scope.md` (returns `"draft"`, `"approved"`, or `""` when the file or key is missing; ignore a trailing `# …` comment, as in `src/cairn/assets/seed/00-charter/scope.md`). Used by US1, US3 and US4 (depends on T003, same file).
- [ ] T005 Update existing tests broken by T001–T003, then run `python3 -m pytest tests/unit tests/integration -q` and fix only failures caused by the bump or the new field. Golden expected-file mismatches are fixed later: mark those cases `xfail(reason="006: relevance added in T014/T015/T031")` for now. Updates: UNIT `--version` assertion → `observe.py 0.6.0`; `tests/integration/test_git.py` → `cairn 0.6.0`; `tests/unit/test_ingest_script.py` `framework_version` → `0.6.0`; `tests/integration/test_init.py` `framework_version`, and assert `_templates/observation.md` has a `relevance:` key directly after `questions:`; BUNDLE: add `relevance` to `NEW_FIELDS`, and the `cairn refresh` case expects `framework 0.5.0 → 0.6.0` and a refreshed template containing `relevance`; `tests/integration/test_charter_bundle.py` and `tests/integration/test_ingest_bundle.py` refresh messages `→ 0.6.0`. Do not change `tests/integration/test_refresh.py` cases that use their own fixture versions.
- [ ] T006 [P] Extend HARNESS for extract-observations scenarios (needed by T018, T032, T038): (a) a `progress` key `{S-ID: {state, questions, steering}}` written to `.cairn/work/extract-observations/progress.json` before the run; (b) a `charter` key mapping `hypotheses.md`, `assumptions.md`, `scope.md` to file content, written to `00-charter/` before the run (when absent, keep whatever the fixture has); (c) when a scenario omits `questions`, keep the fixture's own `00-charter/questions.md`; (d) expect keys `transcript_not_contains` (list of strings) and `new_match_fraction` (`{patterns: [...], min: 0.9}`: at least `min` of the regexes each match some new `O-*.md`). Document all keys in the module docstrings of `tests/skill_eval/conftest.py` and `tests/skill_eval/test_scenarios.py`. Existing charter, ingest and extract-observations scenarios must load and run unchanged.

**Checkpoint**: `python3 -m pytest` is green apart from the golden cases marked `xfail` in
T005; new engagements get `relevance` in `_templates/observation.md`; old ones get
`template-outdated` until `cairn refresh`.

---

## Phase 3: User Story 1 - Only charter-relevant claims become observations (Priority: P1) 🎯 MVP

**Goal**: Every observation the skill writes is tagged to at least one usable question and
carries a one-line `relevance` reason; off-charter claims produce no observations.

**Independent Test**: In the synthetic `FIX/us6-relevance` engagement (3 questions, 2
hypotheses), run `/extract-observations S-001`. Every new observation has a question tag
and `relevance`; no seeded off-charter claim becomes an observation; ≥ 90% of the seeded
relevant claims do (SC-001, SC-002).

### Tests for User Story 1 (write first, confirm they fail)

- [ ] T007 [US1] In UNIT, add `add` refusal tests (contracts/observe-script.md §add, checks in order): `questions: []` → `untagged`; `relevance` missing or `"   "` → `relevance-missing`; `relevance` containing `\n` → `bad-value`; `relevance` of 241 characters → `bad-value`, 240 accepted; a draft tagged `["Q-001","Q-003"]` with `relevance: "Q-001: names a re-keying step"` → `relevance-unlinked` whose detail names `Q-003`; `relevance` equal to the claim, or to a substring of it after normalising (lower case, collapsed whitespace, `Q-###:` prefixes removed) → `relevance-restates-claim`; a tag to a `rejected` and to a `superseded` question → refusal `question-retired` (not a warning; `accept_warnings` cannot accept it); a valid draft writes `_inbox/O-###.md` whose `relevance` equals the input and sits directly after `questions`. `verify`: an observation without `relevance` (copy one from `FIX/us4/_inbox/`) passes; one with a multi-line `relevance` → `bad-value`; one where a later `tag` added a question not named in `relevance` passes. `tag O-ID Q-ID` on a rejected question → `question-retired`.

### Implementation for User Story 1

- [ ] T008 [US1] In SCRIPT, add `check_relevance(d: dict, chk: Check) -> None` and call it in `cmd_add` directly after `check_questions`, implementing the five checks in the order in contracts/observe-script.md §add: `untagged`; `relevance-missing`; `bad-value` (line break, or more than 240 characters); `relevance-unlinked` (every tagged Q-ID must appear as a token in `relevance`; detail lists the missing IDs); `relevance-restates-claim` (normalise both: lower case, collapse whitespace, strip `Q-\d{3,}:` prefixes; refuse when normalised relevance equals or is contained in the normalised claim). All are refusals (depends on T007).
- [ ] T009 [US1] In SCRIPT `check_questions`, make a tag to a `superseded` or `rejected` question the refusal `question-retired` (was a warning); apply the same refusal in `cmd_tag` (contracts/observe-script.md §tag) (depends on T008, same file).
- [ ] T010 [US1] In SCRIPT `verify_one`, when an observation has a `relevance` key, check it is a string with no line break, else report `bad-value`; never check Q-ID linkage there and never report a missing `relevance` (contracts/observe-script.md §verify; contracts/observation-file.md invariant 10) (depends on T009, same file).
- [ ] T011 [US1] In WRITING, add a `## Relevance` section (research R9, FR-014) containing: the test "Would this help answer a usable charter question, or confirm or reject a hypothesis or assumption linked to one?"; how to use each hypothesis's `confirm_if` and `reject_if`, the assumptions that list a question, and the scope's in-scope and out-of-scope lists (a claim touching only an out-of-scope topic is not relevant, FR-006); a synthetic two-column table of relevant vs off-charter claims covering introductions, past employers, anecdotes about another company, office tools, scheduling, stakeholder background, and a wish not covered by any question (and the same wish when a capabilities question exists: stated as the speaker's wish, never as a requirement); the edge cases from spec § Edge Cases (relevant only through context; stakeholder background; borderline → leave out); the rule "unsure → leave it out and list its topic under Passed over; never propose with a weak tag" (FR-007); the `relevance` format `Q-001: <how it bears>; Q-003: <how it bears>` — one line, ≤ 240 characters, names every tagged question, never repeats the claim — with three good and two bad synthetic examples; and that a tag is added only when the claim bears on that question directly (FR-005).
- [ ] T012 [US1] In WRITING, rewrite "Tagging and steering": remove "With no focus, keep every factual claim…" and the "Untagged" text (around lines 113–114); state that every draft has at least one tag and a `relevance`; a focus narrows relevance further; perspective changes which relevant claims are favoured, never whether an off-charter claim is kept. Add granularity guidance (research R8, FR-008): split a passage only when each part is relevant on its own; record a repeated point once, citing its clearest occurrence; background detail inside a relevant passage stays in the quote and gets no observation of its own; a synthetic example where one anecdote yields one observation, not five (depends on T011, same file).
- [ ] T013 [US1] In SKILL: set the front-matter `description` exactly to contracts/extract-observations-skill.md § Front matter (one line, double-quoted); add Never rule 9 ("Never propose a claim that bears on no usable charter question. Never tag a question without saying, in `relevance`, how the claim bears on it."); in Step 2, Read `00-charter/questions.md`, `hypotheses.md`, `assumptions.md` and `scope.md` (skip any that is missing) and keep for the session each usable question, its hypotheses' `confirm_if`/`reject_if`, the assumptions that list it, and the in/out-of-scope lists; in Step 3, "no focus" means every **charter-relevant** claim; in Step 4, apply WRITING § Relevance to each candidate before drafting — relevant → draft with `questions` and `relevance`; off-charter or unsure → don't draft, note its topic and locator for the summary — and add `relevance` to the draft JSON example; in Step 6, remove the `Untagged:` group (around lines 170 and 187) and change the steering line to `none (every charter-relevant claim)`.
- [ ] T014 [P] [US1] Update `FIX/us1/drafts.json` and `FIX/us1/expected/O-*.md`: add a `relevance` (format from T011, naming every tagged Q-ID) to every draft and the identical value to the matching expected file's front matter after `questions`. For the two untagged drafts (expected `O-005.md`, `O-006.md`): if the claim bears directly on a fixture question, tag it and add `relevance`; otherwise delete the draft and its expected file and renumber the later expected files. Remove the T005 `xfail` marks for us1 in GOLDEN.
- [ ] T015 [P] [US1] As T014, for `FIX/us2/drafts-focus.json` + `FIX/us2/expected/` (one untagged draft) and `FIX/us3/drafts.json` + `FIX/us3/expected/` (one untagged draft; expected `O-007.md`). Remove the matching `xfail` marks in GOLDEN.
- [ ] T016 [P] [US1] Create the synthetic fixture `FIX/us6-relevance/` by the hand-built source rule: `engagement.md`; `00-charter/questions.md` with three questions (Q-001 what fulfilment costs per order, Q-002 whether north-site staffing is enough, Q-003 why order-to-ship time is slow); `00-charter/hypotheses.md` with two hypotheses linked to Q-002 and Q-003, each with `confirm_if`/`reject_if`; `00-charter/assumptions.md` with one assumption listing Q-001; `00-charter/scope.md` (`charter_status: approved`; out of scope: org design and hiring); `10-sources/extracted/S-001.md`, a meeting transcript of about 120 turns (`**Name** [T#]:` format) with ~10 seeded relevant claims (at least one bearing only on a hypothesis's `reject_if`, one relevant only through context), seeded off-charter topics of ≥ 3 turns (introductions T1–T8, a past project at another company, office chat tools, an out-of-scope org-design/hiring discussion, a planned warehouse move that may matter but fits no question), and exactly 5 one- or two-turn asides; its `10-sources/index.md` row; and `answer-key.md` listing each seeded relevant claim (locator, question, a regex for the eval), each off-charter topic (label keyword, locator range, a regex that must not appear in any observation), the brief-aside count (5), and the topic that should get the "May matter" line.
- [ ] T017 [US1] Create `FIX/us6-relevance/drafts.json` (one draft per seeded relevant claim in `answer-key.md`, each with `questions` and `relevance`) and add a GOLDEN case `us6-relevance`: copy the fixture to `tmp_path`; `ingest.py verify` reports no problems (`original-missing` warning expected); `observe.py add drafts.json` writes them all; every written file has `relevance`; `observe.py verify` exits 0 (depends on T010, T016).
- [ ] T018 [P] [US1] Create EVAL `us6-relevance.yaml`: `fixture: golden/us6-relevance` (no `questions` key, so the fixture's charter is kept); turn `/extract-observations S-001`; expect `none_new_match: ["^questions: \\[\\]$"]` plus each off-charter topic regex from `answer-key.md`; `per_source.S-001.all_match: ["^relevance: \".+\"$", "^questions: \\[\"Q-"]`; `new_match_fraction: {patterns: <seeded relevant-claim regexes>, min: 0.9}` (SC-001, SC-002) (depends on T006, T016).
- [ ] T019 [US1] Update BUNDLE: SKILL's `description` equals the 006 contract string; WRITING contains `## Relevance` and no longer contains `keep every factual claim` or `Untagged` (depends on T011–T013).

**Checkpoint**: `python3 -m pytest tests/unit/test_observe_script.py tests/integration/test_observe_golden.py tests/integration/test_observe_bundle.py -q` is green (us4 golden still `xfail` until T031); with `CAIRN_SKILL_EVAL=1`, `us6-relevance` passes. This is the MVP.

---

## Phase 4: User Story 2 - See what was passed over (Priority: P2)

**Goal**: The summary lists each off-charter topic of ≥ 3 turns (or a paragraph) with a
locator range, counts brief asides on one line, flags material that may matter with
`/charter`, and flags a source whose count exceeds `density_limit`. Nothing is written for
passed-over material.

**Independent Test**: Run the skill on `FIX/us6-relevance`: the summary has "Passed over"
with each seeded ≥ 3-turn topic and `other brief remarks: 5`, and no file mentions them.
Run it on `FIX/us8-density`: the summary shows the "High density" line and every seeded
claim is still proposed.

### Tests for User Story 2

- [ ] T020 [US2] In UNIT, add `prepare` tests for `density_limit` (data-model §5a): a 120-turn transcript → `12`; a 5-turn transcript → `1`; a paged document of N pages → `N`; an unpaged markdown document (headings/paragraphs only) → `null`; the limit covers the whole source and is not reduced by steering exclusions. Build the sources in `tmp_path` by the hand-built source rule (depends on T007, same file).

### Implementation for User Story 2

- [ ] T021 [US2] In SCRIPT `cmd_prepare`, add `density_limit` to the output: `max(1, turns // 10)` when the units are transcript turns (`T#` locators), `max(1, pages)` when they are pages (`p. #`), else `None` (research R11). Add no refusal or warning tied to it (depends on T010, T020).
- [ ] T022 [US2] In SKILL Step 4, note `prepare`'s `density_limit` and keep a running total of the `written` counts `add` returns for each source in this run. In Step 6, add (contracts/extract-observations-skill.md § Step 6): the "Passed over as off-charter (no observations written):" section exactly as in the contract example — one `<label> · <locator range>` line per distinct off-charter topic of about 3 or more turns or a paragraph or more, unsure claims handled the same way, shorter asides counted on `other brief remarks: N` and never labelled, and one `May matter, fits no current question: <label> · <range> → consider /charter` line per topic that looks important but fits no question (never create the question); and the per-source line `High density: S-### — <n> observations from <turns> turns (flag above <limit>); consider a narrower focus, e.g. /extract-observations S-### for Q-###` (say `pages` for paged sources), shown only when the run's total exceeds a non-null `density_limit`. State that nothing is dropped because of the count and that the 005 natural break still applies. State that passed-over material is never written to any file, drafts file or log (FR-010) (depends on T013, same file).
- [ ] T023 [US2] In WRITING § Relevance, add the "Passed over" size rule (research R7): label topics of about 3 or more turns or a paragraph or more; count shorter asides; a social call with nothing relevant yields few or no observations and the summary says so plainly — a normal result, not an error (depends on T012, same file).
- [ ] T024 [P] [US2] Create the synthetic fixture `FIX/us8-density/` (hand-built source rule): `00-charter/` copied from `FIX/us6-relevance/`, `engagement.md`, `10-sources/index.md`, and `10-sources/extracted/S-001.md`, a 30-turn transcript in which nearly every turn states a distinct claim bearing on Q-001–Q-003 (≥ 6 distinct seeded relevant claims, so an honest run exceeds `density_limit` 3); plus `answer-key.md` listing each claim's locator, question and regex.
- [ ] T025 [US2] Add a GOLDEN case: `prepare S-001` returns `density_limit: 3` on `FIX/us8-density` and `12` on `FIX/us6-relevance` (depends on T021, T024).
- [ ] T026 [US2] Extend EVAL `us6-relevance.yaml`: `transcript_contains: ["Passed over", "other brief remarks: 5", "/charter"]` plus one label keyword per seeded ≥ 3-turn topic from `answer-key.md`; and assert that, apart from new `_inbox/O-*.md`, `progress.json` and the changelog, no file in the engagement changed (use `unchanged_files`) (depends on T018).
- [ ] T027 [P] [US2] Create EVAL `us8-density.yaml`: `fixture: golden/us8-density`, turn `/extract-observations S-001`; expect `transcript_contains: ["High density", "narrower focus"]` and `new_match_fraction: {patterns: <every seeded claim regex from FIX/us8-density/answer-key.md>, min: 1.0}` (FR-016: nothing dropped) (depends on T006, T024).

**Checkpoint**: US1 and US2 both pass on their own; unit and golden tests are green.

---

## Phase 5: User Story 3 - Charter changes bring in new evidence (Priority: P2)

**Goal**: A `done` source can be re-run with or without a focus, without confirmation; the
skill proposes only claims no observation holds and offers to retag existing ones. `status`
shows which questions a finished source predates.

**Independent Test**: In `FIX/us6-relevance`, seed `progress.json` with S-001 `done` for
Q-001–Q-003 and existing observations for its relevant claims, add Q-004 matching a seeded
off-charter topic, and run plain `/extract-observations S-001`: no confirmation is asked;
the Q-004 claims are proposed; nothing already held is proposed again (SC-006).

### Tests for User Story 3

- [ ] T028 [US3] In UNIT, add tests: `progress S-001 --done` stores `questions` = sorted usable question IDs (rejected/superseded excluded); adding Q-004 afterwards makes `status` report `new_questions: ["Q-004"]` for S-001; a 005-era `done` entry without `questions` → `new_questions: []`; a source not `done` → `new_questions: []`; `prepare S-001` on a `done` source exits 0 without `--confirmed`; on a re-run, `add` still refuses a draft matching an existing observation with `duplicate` (depends on T020, same file).

### Implementation for User Story 3

- [ ] T029 [US3] In SCRIPT `cmd_progress`, when `--done`, also store `"questions": usable_questions(eng)` in the source's entry; `--stopped-at` is unchanged. In `cmd_status`, add `new_questions` to each source dict: usable question IDs not in `progress.questions`, sorted; `[]` when the state isn't `done` or the entry has no `questions` (data-model §4, contracts/observe-script.md §status) (depends on T021, T028).
- [ ] T030 [US3] In SKILL: Step 1 notes each source's `new_questions` and, with no arguments, lists `done` sources that have `new_questions`, e.g. `S-001 — processed before Q-005; re-run with /extract-observations S-001`; Step 3: a `done` source named in the arguments is processed without asking — with a focus, against the focus questions; with no focus, against every usable question — relying on `existing` and `add`'s `duplicate` and `previously-rejected` refusals to keep it to new claims (FR-013); Step 5: retagging is offered with a focus (as in 005) and on a plain re-run of a `done` source with `new_questions` — list existing observations that bear on a new question but lack its tag, and ask once (research R6) (depends on T022, same file).
- [ ] T031 [P] [US3] Update `FIX/us4/drafts-rerun.json` and `FIX/us4/expected/O-021.md`: add `relevance` to every draft and expected file; tag the two untagged drafts to a fixture question with `relevance` so the refusal each was built to show (e.g. `duplicate`) still fires, or remove a draft that only demonstrated untagged extraction. Do not touch `FIX/us4/_inbox/` (pre-006 observations without `relevance` must keep passing `verify`). Remove the remaining T005 `xfail` marks in GOLDEN and assert `verify` exits 0 on `FIX/us4`.
- [ ] T032 [P] [US3] Create EVAL `us7-new-question-rerun.yaml`: `fixture: golden/us6-relevance`; `questions` = the fixture's Q-001–Q-003 plus Q-004 whose title matches the seeded "planned warehouse move" topic in `answer-key.md`; `progress: {S-001: {state: done, questions: [Q-001, Q-002, Q-003]}}`; `existing` = observations for the seeded Q-001–Q-003 claims; turn `/extract-observations S-001`. Expect: `transcript_not_contains` confirmation phrasing (e.g. "already processed. Re-run", "confirm"); `new_match_fraction` over the Q-004 seeded regexes with `min: 0.9` (SC-006); `none_new_match` for every Q-001–Q-003 seeded regex (no duplicates); `progress_state: {S-001: done}` (depends on T006, T016).
- [ ] T033 [US3] Run EVAL `us4-rerun.yaml` and update it only if T031 changed the drafts or IDs it relies on; it must pass with `relevance` on its outputs (depends on T031).

**Checkpoint**: US1–US3 pass independently; `status` shows `new_questions`; a re-run proposes only new claims.

---

## Phase 6: User Story 4 - No charter, no extraction (Priority: P3)

**Goal**: With no usable questions, the skill stops before reading any source and points to
`/charter`; with only proposed questions (draft charter), it extracts and says the charter
isn't approved.

**Independent Test**: In a synthetic engagement with no questions, run the skill on an
ingested source: no source is read, nothing is written, `/charter` is suggested.

### Tests for User Story 4

- [ ] T034 [US4] In UNIT, add tests: with `00-charter/questions.md` empty, or holding only `rejected`/`superseded` questions, `prepare S-001` and `add drafts.json` exit 6 with exactly `{"error": "no-questions", "message": "The charter has no active or proposed questions. Run /charter first."}`; during `prepare` the source file is `chmod 000` to prove it was not opened; `add` writes nothing (checked before any draft); `status` still exits 0 with `usable_questions: 0`; `status` reports `charter_status` `"draft"`, `"approved"`, and `""` when `00-charter/scope.md` is missing; with only `proposed` questions, `prepare` and `add` succeed (depends on T028, same file).

### Implementation for User Story 4

- [ ] T035 [US4] In SCRIPT, add the `no-questions` gate: in `cmd_prepare` after the policy gate and before the source gate, and in `cmd_add` before any draft is checked, raise `Fail(6, …)` with the T034 payload when `usable_questions(eng)` is empty. In `cmd_status`, add top-level `charter_status` (from `charter_status(eng)`) and `usable_questions` (the count); `status` never refuses for lack of questions (contracts/observe-script.md §status, §prepare, §add) (depends on T029, T034).
- [ ] T036 [US4] In SKILL Step 2: `usable_questions: 0` → say the charter has no questions to judge relevance against, suggest `/charter`, and stop — read no source, write nothing (replaces 005's "continue untagged" path); `charter_status: draft` → carry on against the proposed questions and, in Step 6, add the line `Charter not yet approved: questions are proposed` (FR-011, FR-012) (depends on T030, same file).
- [ ] T037 [P] [US4] Update EVAL `us2-no-questions.yaml`: rename it to "No questions in the charter stops and suggests /charter (006 US4)"; keep `questions: []` and `new_count: [0, 0]`; keep `transcript_contains: ["/charter"]`; add `no_source_reads: true`.
- [ ] T038 [P] [US4] Create EVAL `us9-draft-charter.yaml`: `fixture: golden/us6-relevance`; `questions` = the fixture's three questions, all `status: proposed`; `charter: {scope.md: <the fixture's scope.md with charter_status: draft>}`; turn `/extract-observations S-001`; expect `new_count: [1, 30]` and `transcript_contains: ["Charter not yet approved"]` (FR-012) (depends on T006, T016).

**Checkpoint**: All four stories pass independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Point the 005 and 001 design docs at 006, run every check, and hand over the
manual check.

- [ ] T039 [P] In `specs/005-extract-observations/spec.md` and `specs/005-extract-observations/research.md`, add a dated note (2026-11-09) at the "every factual claim" clarification and at decision R1: "Replaced by 006-charter-relevant-observations: only charter-relevant claims are proposed; no untagged observations." Keep the original text.
- [ ] T040 [P] Amend `specs/005-extract-observations/contracts/observe-script.md`, `contracts/extract-observations-skill.md`, `contracts/observation-file.md` and `specs/005-extract-observations/data-model.md` so each changed section matches the 006 deltas in `specs/006-charter-relevant-observations/contracts/` and `data-model.md` (`relevance`, the new refusal codes, `question-retired` as a refusal, `no-questions`, `density_limit`, the `status` keys, `progress.questions`, the Step 6 summary), each with a one-line "Changed by 006" pointer. BUNDLE's 005-contract assertions must still pass.
- [ ] T041 [P] In `specs/001-engagement-init/data-model.md`, add `relevance` to the `observation` row of the template table and one sentence: `extract-observations` (006) writes it on every new observation; hand-written and pre-006 observations may leave it empty.
- [ ] T042 [P] Update `tests/fixtures/observe/README.md`: list the new `us6-relevance` and `us8-density` fixtures, that they are hand-built and synthetic, what `answer-key.md` holds, and that `FIX/us4/_inbox/` deliberately keeps pre-006 observations without `relevance`.
- [ ] T043 Re-read SKILL and WRITING end to end against spec FR-001–FR-016 and contracts/extract-observations-skill.md: no text still says "every factual claim", "untagged" or "Untagged"; FR-015 behaviours (citation, exact passages, locators, speaker attribution, confidence caps, derived flags, steering, natural breaks, Never rules 1–8) are unchanged.
- [ ] T044 Run `python3 -m pytest -q` (whole suite, including `tests/integration/test_observe_perf.py`), confirm no `xfail` marks from T005 remain, and fix any failure; check each expected bullet of quickstart §1.
- [ ] T045 Run `CAIRN_SKILL_EVAL=1 python3 -m pytest tests/skill_eval -k extract-observations -q` (quickstart §2) and record pass/fail per scenario (us6, us7, us8, us9, updated us2, and every 005 scenario) in `specs/006-charter-relevant-observations/checklists/requirements.md` under a dated "Eval results" heading.
- [ ] T046 Consultant's manual check (quickstart §3; trial data never enters the repository): in the trial engagement run `cairn refresh`, set aside the 005-era `_inbox/` files, run `/extract-observations S-001`, and check SC-003 (≥ 60% fewer than 157), SC-004 (≥ 18 of 20 relevance reasons agreed), SC-005 (triage under 20 minutes), the Passed over list, and the High density line if it applies. Record only counts and pass/fail in `specs/006-charter-relevant-observations/checklists/requirements.md`.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories.
- **US1 (Phase 3)**: needs Phase 2. The MVP.
- **US2 (Phase 4)**: needs Phase 2; extends US1's `us6-relevance` scenario (T026 after T018) and follows US1 in the shared files.
- **US3 (Phase 5)**: needs Phase 2 and the `us6-relevance` fixture (T016); follows US2 in the shared files.
- **US4 (Phase 6)**: needs Phase 2 (`usable_questions`, `charter_status` from T004); follows US3 in the shared files.
- **Polish (Phase 7)**: after the stories being shipped.

Each story has its own independent test, but because they share SCRIPT, SKILL, WRITING and
UNIT, implement them in priority order: US1 → US2 → US3 → US4.

### Same-file chains (must run in this order)

- **SCRIPT**: T001 → T003 → T004 → T008 → T009 → T010 → T021 → T029 → T035
- **UNIT**: T005 → T007 → T020 → T028 → T034
- **SKILL**: T013 → T022 → T030 → T036
- **WRITING**: T011 → T012 → T023
- **GOLDEN**: T005 (xfail) → T014/T015 → T017 → T025 → T031
- **EVAL us6-relevance.yaml**: T018 → T026
- **HARNESS**: T006 only

### Within each story

- Unit tests first; confirm they fail; then the script change.
- Script change before the SKILL text that relies on its output.
- Fixtures before the golden cases and evals that use them.

---

## Parallel Opportunities

- Phase 2: T002 (TEMPLATE) and T006 (HARNESS) alongside the SCRIPT chain T003 → T004.
- US1: T014, T015, T016 (separate fixture folders) and then T018 (new eval file) alongside the UNIT → SCRIPT and WRITING → SKILL chains.
- US2: T024 (fixture) and T027 (eval) alongside T020 → T021 and T022/T023.
- US3: T031 (us4 fixture) and T032 (eval) alongside T028 → T029 → T030.
- US4: T037 and T038 (eval files) alongside T034 → T035 → T036.
- Polish: T039–T042 are all different files.

### Parallel example: User Story 1

```text
# Chain A (sequential, shared files):
T007 UNIT tests → T008 check_relevance → T009 question-retired → T010 verify
T011 WRITING Relevance → T012 WRITING Tagging → T013 SKILL steps → T019 BUNDLE

# In parallel with chain A:
T014 FIX/us1 relevance
T015 FIX/us2 + FIX/us3 relevance
T016 FIX/us6-relevance fixture + answer key → T018 EVAL us6-relevance.yaml
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 + Phase 2 (version, template field, helpers, harness keys).
2. Phase 3 (US1): the script refuses untagged and unexplained drafts; the skill applies the
   relevance test; the golden fixtures carry `relevance`.
3. **Stop and validate**: unit, golden and bundle tests green; the `us6-relevance` eval
   meets SC-001 and SC-002. This alone addresses the 157-observation flood.

### Incremental delivery

1. + US2: the consultant sees what was passed over, and when a source is unusually dense.
2. + US3: re-runs after charter changes recover passed-over evidence.
3. + US4: hard stop with no questions; draft-charter note.
4. Polish: 005/001 docs point to 006; full suite and evals; the consultant's manual check (T046).

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- Commit after each task or logical group. Golden cases are `xfail` only between T005 and
  T014/T015/T031; T044 confirms none remain.
- Each checkpoint names the command that proves the story.
