# Research: Extract Observations Skill

Phase 0 decisions for `specs/005-extract-observations/spec.md`. Each entry gives the
decision, why, and what else was considered. Numbering continues the R-style of 002–004.

## R1. Default breadth with no focus (spec clarification)

- **Decision**: With no focus, the skill extracts **every factual claim** in the source.
  Claims that bear on no charter question are written with `questions: []` and listed
  under "Untagged" in the summary.
- **Rationale**: Confirmed by the project owner (2026-11-05). FR-024 already lists
  untagged observations. SC-005 (80% of known key findings covered) needs recall, and
  questions change over time (US4), so dropping untagged claims would lose evidence that a
  later question needs.
- **Alternatives considered**: Only question-relevant claims (smaller inbox, lower recall).
  Every claim with a cap per source (adds a second stopping rule next to the long-source
  break; deferred until a trial shows inboxes are too large).

## R2. Split of work: the assistant judges, the script checks and writes

- **Decision**: Follow the `ingest` pattern. The assistant reads the source and decides
  what the claims are, how to word them, which passage and locator back each one, which
  questions they bear on, and the confidence. It writes them as **drafts** in a JSON file.
  A helper script, `scripts/observe.py`, then:
  - checks every draft deterministically (quote word for word at the locator, inside the
    content region, not excluded, confidence within the cap, question IDs exist, no exact
    duplicate);
  - fills every field it can work out for itself (`id`, `origin`, `derived`, `speaker`,
    `status`, `audience`, `created`, `source`);
  - writes each accepted draft as `_inbox/O-###.md`.
- **Rationale**: Principle I allows scripts where a deterministic check beats instructions:
  ID assignment, and here also SC-001 and SC-002 (100% field completeness and quote
  fidelity, "as confirmed by an automated check"). Fields the model could get wrong but the
  script can compute (derived flag, speaker name, origin, confidence cap) are computed, not
  asked for.
- **Alternatives considered**: The assistant writes observation files itself and a
  `verify` command checks them afterwards. It works, but wrong files land in `_inbox/`
  first, numbering races with hand-written files, and the assistant must copy eight
  fields per file that it can't improve. Instructions only: SC-001/SC-002 couldn't be
  guaranteed.

## R3. Script location, Python version and shared code

- **Decision**: `skills/extract-observations/scripts/observe.py`, standard library only,
  Python **3.9+**, run as `python3 <skill base directory>/scripts/observe.py <command>`.
  It copies the parsing helpers it needs from `ingest.py`: front matter and value parsing,
  finding the engagement, atomic write, changelog append, ID scanning, and the content-unit
  splitting and normalisation that `verify` uses to find a locator. The parity test is
  extended to cover all three scripts.
- **Rationale**: Same constraints as 002 R3 and 003 R3: skills ship and refresh as separate
  folders and run under the consultant's `python3`.
- **Note on the deferred shared module**: 003 R3 deferred a shared module "until a third
  skill needs the same code". This is that third skill. Extracting the module now means
  refactoring `charter.py` and `ingest.py` inside this feature, which is outside its scope
  and adds risk to two shipped skills. The plan keeps the copy, extends the parity test,
  and records the extraction as a follow-up (plan, Complexity Tracking).
- **Alternatives considered**: A byte-identical `scripts/cairn_common.py` in all three
  skills, enforced by a test (cleanest; deferred as above). Importing `ingest.py` by path
  (breaks if skills are refreshed or removed separately).

## R4. Where the quoted passage and speaker live

- **Decision**: The observation template gains:
  - front matter `speaker: ""` (the confirmed name, else the original label; transcripts
    only), `translated: false`, and `passage_kind: ""` (`text`, `table-row`, `comment`,
    `tracked-change`);
  - two body sections: `## Claim` (the one claim, in a sentence) and `## Passage` (the exact
    words, as a `> ` block quote).
- **Rationale**: Passages can be long and contain quotes, colons and line breaks. The
  scripts' minimal YAML parser reads single-line values only, so the passage belongs in the
  body. A block quote is also what a consultant reads fastest during triage (SC-006).
  `passage_kind` lets `verify` and `triage` check the FR edge cases on comments and tracked
  changes without parsing the wording.
- **Alternatives considered**: Front-matter `quote:` (escaping problems, hard to read).
  Locator only, no passage (fails FR-012 and the "check in seconds" goal).

## R5. Locator grammar and how quotes are checked

- **Decision**: An observation's locator is an `ingest` locator (003 data-model §3.4),
  optionally refined for tables:
  - `p. 2`, `§ Process manual > Receiving`, `¶ 12`, `00:14:32` or `T17`,
    `comment 3 @ § Background`;
  - table refinement: `<unit> › table <n> › row <m>` with an optional `› <column header>`
    (tables counted from 1 within the unit; rows counted from 1 among data rows, after the
    header).
  The script finds the unit with the same splitting `ingest verify` uses, normalises
  whitespace and markdown markers (`**`, `> `, table pipes) on both sides, and requires the
  quote to be a **contiguous** substring of the unit (or of the row, for table locators).
  No ellipses: a claim that needs two separated pieces of text is a combined claim and
  isn't an observation (FR-010). A minimum quote length of 3 words, except table rows.
- **Rationale**: FR-011/012, US1 scenario 8, SC-002. Reusing ingest's units means a locator
  the consultant sees in the source file is exactly the one the check uses.
- **Alternatives considered**: Fuzzy matching (hides real misquotes). Character offsets
  (unreadable to people, and break on an `extraction-fix`).

## R6. Derived, uncertain, speaker and origin are computed from the source

- **Decision**: For each accepted draft, the script reads the source and sets:
  - `derived: true` when the quote lies in a `[!derived]` callout or a `[!corrected] … ·
    derived` callout (FR-016);
  - `passage_kind` from where the quote lies (table row, `[!comment]`, `{++ ++}`/`{-- --}`
    tracked change, else text);
  - `speaker` from the turn's label and the `## Speakers` table (confirmed name, else the
    label) (FR-013, US3-1);
  - `origin` copied from the source; a source with origin `llm-inference` is refused
    (FR-014);
  - the **confidence cap**: the source's confidence; `medium` for `author_kind:
    ai-notetaker`; `low` when the locator matches an entry in `uncertain_passages`
    (FR-015). A draft above the cap is refused with code `confidence-cap`; a draft
    under an uncertain passage must also name it in its reason (the script prefixes
    "uncertain extraction: " if the reason doesn't say so).
- **Rationale**: These are facts about the source, not judgments; computing them removes a
  whole class of errors.
- **Alternatives considered**: Asking the assistant to set them and checking afterwards
  (more round trips, same result).

## R7. Wording rules stay in the instructions, with light checks

- **Decision**: Atomicity, no interpretation, attribution ("X said …", "The summary by Y
  reports …"), keeping opinions and estimates as such, and comment/tracked-change framing
  are wording rules in `SKILL.md` and `reference/writing-observations.md`, with worked
  examples. The script adds only warnings it can check reliably:
  - `attribution-missing`: a transcript observation whose claim doesn't contain the speaker
    name or label;
  - `summary-attribution-missing`: a `meeting-notes` observation whose claim doesn't name
    the author or "summary"/"notes";
  - `kind-unstated`: a `comment` or `tracked-change` passage whose claim doesn't say so.
  Warnings make `add` refuse the draft unless the assistant re-sends it with `--accept-
  warning <code>`; the assistant fixes the wording instead in nearly every case.
- **Rationale**: SC-004 is judged by a reviewer, not a script, so the instructions carry
  most of it; the checks catch the most damaging slip (US3: an opinion turned into a fact).
- **Alternatives considered**: An LLM-judge step inside the skill (costly, and not
  deterministic); no checks (US3 failures are invisible later).

## R8. IDs

- **Decision**: Next free `O-###` = 1 + the highest `O-` number found anywhere in the
  engagement's markdown outside `10-sources/raw/` and outside source content regions,
  as `ingest` does for `S-###` (003 R16). This covers `_inbox/`, `30-observations/`, every
  status and hand-written files (FR-020, US4-4). `add` assigns IDs in draft order and
  writes one file at a time, atomically, so an interrupted run leaves a valid prefix.
  File name: `_inbox/O-###.md`.
- **Rationale**: Principle V; mentions outside the two folders (for example a finding that
  already links a hand-numbered observation) must still block reuse.
- **Alternatives considered**: Counting only the two folders (misses IDs referenced
  elsewhere).

## R9. Re-runs: duplicates and rejected claims

- **Decision**:
  - `prepare S-ID` lists every existing observation citing that source, in `_inbox/` or
    `30-observations/`, any status: ID, status, locator, claim, passage, questions. The
    assistant reads it before extracting and drops claims already recorded or rejected
    (FR-022).
  - `add` **refuses** an exact duplicate (same source, same normalised passage, same
    normalised claim) with code `duplicate`, and a rejected match with code
    `previously-rejected`.
  - `add` **warns** `same-passage` when another observation already quotes an overlapping
    passage. The assistant keeps the draft only if it states a different claim (US1-3),
    re-sending with `--accept-warning same-passage`.
- **Rationale**: Exact matching is reliable but too narrow; semantic matching belongs to
  the assistant. The overlap warning forces the comparison at the right moment.
- **Alternatives considered**: Script-only fuzzy claim matching (false positives on
  US1-3's legitimate split claims).

## R10. Adding question tags to existing observations

- **Decision**: `tag O-ID Q-ID [Q-ID …]` adds the question IDs to the observation's
  `questions` list, changing no other field, and appends one changelog line per
  observation:
  `YYYY-MM-DD · O-012 · tag · added Q-006 · -`.
  This is a new event, `tag`, added to the shared change convention (all copies) and the
  changelog seed. The skill runs `tag` only after the consultant confirms (FR-023, US4-3).
- **Rationale**: A tag isn't a claim change, so `clarify` (which needs previous wording) and
  `relink` (a link *moving* between versions) don't fit; `what-changed` should be able to
  tell "new evidence tagged to Q-006" apart from either.
- **Alternatives considered**: Reusing `relink` with subject `O-012: + Q-006` (blurs two
  meanings); not logging (fails FR-023).

## R11. Steering input

- **Decision**: The assistant parses the free-text steering from the arguments
  (`for Q-003 …`, `ignore the appendix`, `from the warehouse manager's point of view`) and
  writes it, resolved, into the drafts file header:
  `focus: [Q-003]`, `exclude: ["p. 14–22", "§ Appendix"]`, `perspective: "…"`.
  - `focus` must be existing question IDs. With a focus, every draft must be tagged with at
    least one focus question (`add` refuses others with `off-focus`) (US2-2).
  - `exclude` entries are locator prefixes (`§ Appendix`), page ranges (`p. 14–22`) or
    speakers (`speaker: Speaker 3`). `add` refuses drafts inside them (`excluded`) (US2-3,
    SC-003).
  - `perspective` is a judgment for the assistant only; it is echoed in the summary
    (US2-4).
  The assistant confirms its reading of the steering in one line before extracting when an
  exclusion is ambiguous ("the appendix = § Appendix A and § Appendix B?").
- **Rationale**: Exclusions and focus are checkable, so they're checked (SC-003 asks for
  zero). Perspective isn't.

## R12. Long sources, interruption and progress

- **Decision**: The assistant works through a source **unit by unit** (page, top-level
  section, or block of about 40 turns) and calls `add` after each unit or small group, so
  files land as it goes. `progress S-ID --stopped-at <locator>` records a natural break in
  `.cairn/work/extract-observations/progress.json`, with the steering used; `progress S-ID
  --done` marks a full pass. On the next run, `prepare` returns `resume_from` and the
  previous steering; the skill offers to continue from there. An interrupted run needs no
  record: written observations are complete, and R9 skips them.
  Break rule in the instructions: stop after about 40 proposed observations in one session,
  at the end of the current unit.
- **Rationale**: Edge cases "very long source" and "run interrupted". Committing as it goes
  bounds the loss on interruption to one unit.
- **Alternatives considered**: Recording progress in the source's front matter (the source
  is `ingest`'s object, and its fields belong to that skill).

## R13. Gates: policy, restriction, source state

- **Decision**: `status` and `prepare` read `engagement.md` and the source front matter
  (the assistant never reads `engagement.md`, as in 002 R7) and refuse with exit 3 when:
  `model_use: unconfirmed` (refuses everything, FR-005); the source is `restricted` or
  `content_removed` (FR-006). Exit 6 for `extraction_status: in-progress` or an unknown ID
  (FR-007). `rejected`/`superseded` sources need `--confirmed` (and `prepare` returns the
  superseding source's ID). `proposed` sources are allowed and flagged
  `source_not_approved: true` for the summary. The instructions repeat every gate, and the
  assistant Reads `10-sources/extracted/S-###.md` only after `prepare` succeeds for it.
  `add` re-checks the gates, so a draft citing a refused source can't be written.
  Under `model_use: restricted`, sources already ingested were cleared per file by
  `ingest`; nothing more is asked.
- **Rationale**: Principle VIII is non-negotiable, so it's enforced twice, as in 003 R6.
- **Alternatives considered**: Instructions only (one slip leaks a restricted source).

## R14. Code name

- **Decision**: `status` returns `client_label`. Titles and the summary use it. `add`
  refuses a draft whose title or claim holds the real client name (`real-name-leak`); the
  claim uses the code name instead. The passage is exempt: it is the source's words
  (FR-021).
- **Rationale**: Same rule and check as 003 R17.

## R15. Template and convention changes

- **Decision**:
  - `templates/observation.md`: add `speaker`, `translated`, `passage_kind`, and the
    `## Claim` / `## Passage` body (R4).
  - Change convention: add the `tag` event (R10), in the charter, ingest and new
    extract-observations copies (byte-identical), plus the changelog seed's event list.
  - Update `specs/001-engagement-init/data-model.md` (template table) and
    `specs/002-charter-skill/contracts/change-convention.md` to mirror.
  Engagements on 0.4.0 get the new template and skill through `cairn refresh`; refresh's
  existing rule keeps a consultant-edited template and backs it up.
- **Rationale**: Constitution: a data-model change updates every template and skill that
  uses it, in the same change.

## R16. Framework version

- **Decision**: `__version__` 0.4.0 → **0.5.0**. A new bundled skill and an additive
  template change are a minor version, as for 003 (0.2.0 → 0.3.0).

## R17. Testing strategy

- **Decision**: As in 003 R18, three levels:
  1. **pytest, always run**:
     - `tests/unit/test_observe_script.py`: gates (exit 3 on `unconfirmed` and restricted
       with no read of the file; exit 6 on in-progress); ID numbering across folders,
       statuses and stray mentions; quote matching per format (PDF page, heading path,
       ¶, timestamp/turn, table row and column, comment, derived and corrected callouts);
       refusal of quotes from Context/Description; computed fields; confidence caps;
       focus, exclude, duplicate, rejected, same-passage; leak check; `tag` and its log line;
       `verify`; `raw/` untouched.
     - `tests/unit/test_ingest_parity.py` extended to `observe.py` (or a new
       `test_observe_parity.py`).
     - `tests/integration/test_observe_bundle.py`: `init` ships three skills; `refresh`
       0.4.0 → 0.5.0 adds the skill and the template fields; settings rule for `observe.py`;
       the change-convention copies are identical.
     - `tests/integration/test_observe_golden.py`: a synthetic engagement with
       golden sources (reusing ingest's golden sources) and hand-checked expected
       observations; `verify` passes on them and reports expected codes on broken ones.
     - `tests/integration/test_observe_perf.py`: timing goals.
  2. **Opt-in live-model evaluation** (`CAIRN_SKILL_EVAL=1`):
     `tests/skill_eval/scenarios/extract-observations/*.yaml` for US1–US4 and key edge
     cases (restricted canary, unconfirmed policy, prompt injection, exclusion, re-run).
     The harness asserts on files, `verify` output and transcript text. SC-004 is scored
     by a reviewer from the produced files, using a rubric in the fixtures README.
  3. **Manual**: quickstart §8 on the Phase 1 trial engagement, held locally (SC-005,
     SC-006).
- **Rationale**: Deterministic parts are fully covered automatically; judgment quality is
  measured where it can only be measured.

## R18. No new dependencies or network use

- **Decision**: No new Python dependencies; no poppler use (the skill reads only extracted
  markdown); no web, fetch, library or prior-art tools (FR-009). `SKILL.md`'s
  `allowed-tools` is `Read, Write, Edit, Bash(python3 *observe.py*)`; `Write` is needed for
  the drafts file only, and the instructions forbid writing observation files directly.
- **Rationale**: FR-006, FR-009, Principle VIII.
