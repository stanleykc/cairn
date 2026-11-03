# Research: Charter Skill

Decisions for the `charter` skill. Each one resolves an open point in the plan's Technical
Context or a design choice the spec leaves open. Numbering continues the style of feature
001 (R1, R2, …) but restarts for this feature.

## R1. What the skill is made of

- **Decision**: One Claude Code skill folder, `src/cairn/assets/skills/charter/`, holding:
  - `SKILL.md`: the session flow, the rules and the never-do list.
  - `reference/`: longer guidance, read only when that part of the session is reached
    (interview topics, review and revision, the change convention, filled-in examples).
  - `scripts/charter.py`: one standard-library helper script.
  `cairn init` and `cairn refresh` already copy every folder under `assets/skills/` into
  `.claude/skills/` (feature 001, R10), so FR-001 needs no change to the command.
- **Rationale**: Principle I says skills are instructions first and allows scripts only
  where a deterministic check is more reliable. Keeping `SKILL.md` short and moving detail
  into `reference/` means only the guidance a session needs gets loaded.
- **Alternatives considered**: All the guidance in one large `SKILL.md`, which is harder to
  maintain and loads text the session may not need. Several small skills (`charter`,
  `charter-review`, `charter-revise`), which goes against the single `charter` skill in the
  framework design.

## R2. What the script does, and what the assistant does

- **Decision**: The script handles the deterministic parts. The assistant handles the
  conversation and writes entries by following the templates.

  | Job | Done by | Why |
  |---|---|---|
  | Find the engagement, read its settings | script `status` | Deterministic. Keeps `engagement.md` out of the conversation (R7). |
  | List items, statuses, links, next free IDs | script `status` | ID assignment is named in Principle I as a script job. |
  | Find duplicate or malformed IDs, broken or one-sided links, missing fields | script `status` / `check` | Link checks are named in Principle I as a script job. |
  | Structural gaps (questions with no hypothesis, hypotheses with no `reject_if`, unfilled scope sections) | script `status` | Can be checked from fields alone. |
  | Meaning gaps (objective with no question, deliverable with no date) | assistant | These need the text to be read and understood. |
  | List objects that link to an ID (FR-029) | script `refs` | Must cover the whole engagement without reading client content into the conversation (R6). |
  | Set the model-use policy in both files | script `model-use` | Two files must stay in step, and the authoritative file holds the real client name (R7). |
  | Interview, write Q/H/A entries, scope text, stakeholders, lenses, changelog | assistant | This is the skill's actual work. The templates define the format, and `check` verifies it afterwards. |

  After each write, the assistant runs `check`. If `check` reports a problem it caused, it
  fixes it before moving on.
- **Rationale**: SC-003 and SC-004 need every item to be well formed, with consistent
  links. A deterministic check after each write catches mistakes straight away, while
  writing stays with the assistant, which has to phrase the text anyway.
- **Alternatives considered**:
  - *Instructions only.* ID numbering and two-way links are exactly where language models
    slip, and SC-003/SC-004 need 100%.
  - *The script does every write* (`add-question --title …`). This turns the skill into a
    CLI wrapper, needs long multi-line arguments for body text, and duplicates the
    templates in code.

## R3. Where the script lives and which Python it needs

- **Decision**: The script lives inside the skill folder and is run as
  `python3 <skill base directory>/scripts/charter.py <command>`. Claude Code shows the base
  directory when it loads the skill. The script uses only the standard library and runs on
  **Python 3.9+**: no `match` statements, and `from __future__ import annotations` for type
  hints. It does not import the `cairn` package.
- **Rationale**: The copy in `.claude/skills/` stays at the engagement's framework version,
  like the skill text. It also works for an analyst who opened the engagement without
  installing `cairn`. Python 3.9 is the oldest `python3` on supported Macs (Command Line
  Tools). The `cairn` package itself still requires 3.11.
- **Alternatives considered**: A `cairn charter-check` subcommand. It would depend on the
  installed `cairn` version rather than the engagement's, and would fail for team members
  who don't have `cairn` installed. A shared helper library for all skills can be extracted
  when a second skill (`triage` or `ingest`) needs the same scanning. For now the script
  keeps the parsing in one module so it can be lifted out later.

## R4. Reading charter entries without PyYAML

- **Decision**: A small parser in the script reads:
  - the flat front matter of each file;
  - each `## <ID>: <title>` heading in the collection files, and the fenced `yaml` block
    under it, accepting flat scalars, inline lists (`["Q-001", "Q-002"]` or `[Q-001]`),
    block lists (`- Q-001`) and trailing `# comments`.
  Anything it cannot parse is reported as `malformed` with the file and line. It is never
  guessed at. The skill writes inline lists of quoted IDs, so the files it writes always
  parse.
- **Rationale**: Hand edits must survive (spec edge case: hand-written entries are kept).
  PyYAML isn't available to the script (R3). The subset is the one the templates use.
- **Alternatives considered**: Vendoring a YAML parser into the skill, which is far too
  much code for the subset needed.

## R5. Finding the engagement

- **Decision**: Walk up from the current directory to the first `engagement.md` whose front
  matter has `type: engagement`. If none is found, try the engagement that contains the
  script: `Path(__file__).resolve().parents[4]` (the root of
  `<root>/.claude/skills/charter/scripts/charter.py`), but only if the path has that many
  parents and that folder's `engagement.md` has `type: engagement`. If that fails too, exit with code 2 and
  print: "Not inside a Cairn engagement. Create one with `cairn init`, then run `charter`
  from inside it." (FR-002).
- **Rationale**: Matches how feature 001 recognizes an engagement (`type: engagement`), and
  works whether Claude Code was started at the engagement root or in a subfolder.

## R6. Never reading client documents (FR-006, SC-005)

- **Decision**: Four layers:
  1. **Instructions.** `SKILL.md` says to never open, list or search `10-sources/`, and to
     never read a file the consultant offers. The skill declines, explains why and asks for
     a summary (US2-4). This is in the never-do list at the top of the skill.
  2. **The script never touches `10-sources/`.** `status`, `check` and `refs` scan only the
     content folders that hold Cairn objects, and skip `10-sources/` entirely.
  3. **The script outputs IDs, never other objects' text.** `refs` returns object IDs,
     fields and file paths only. It never returns titles or bodies of observations or
     findings, which can quote client material.
  4. **Tested.** The skill evaluation (R20) puts a synthetic brief with a unique canary
     string in `10-sources/raw/` and `10-sources/extracted/`. It then asks the skill to read
     it, and asserts that no tool call touched `10-sources/` and the canary appears nowhere
     in the transcript or in any file written.
- **Rationale**: Claude Code skills can pre-approve tools but cannot deny them, and a
  project-wide deny rule on `10-sources/` would block `ingest` later. Keeping the script
  away from those folders, and returning IDs only, means the one deterministic component
  cannot leak content even by accident.
- **Alternatives considered**: A `PreToolUse` hook that blocks reads under `10-sources/`
  while `charter` runs. A hook can't tell which skill is active, so it would block `ingest`
  as well. It may be worth revisiting as a framework-wide guard once `ingest` exists.

## R7. Keeping the engagement record out of the conversation

- **Decision**: The assistant never reads `engagement.md`. `status` returns what the skill
  needs from it: `engagement_name`, `client_label` (the code name if set, otherwise
  `client`), `uses_code_name`, `lead_consultant`, `model_use`, `model_use_notes`. When a code
  name is set, the real `client` value is never printed. The `model-use` command writes the
  policy to `engagement.md` and `scope.md` in one step. `check` searches the charter files
  and the changelog for the real client name (case-insensitive) and reports `real-name-leak`
  with the file only, without printing the name.
- **Rationale**: FR-037 is guaranteed most strongly if the real name never enters the
  conversation, so the model cannot write it by accident. It also keeps the record's most
  sensitive field away from an external service while the policy is `unconfirmed`.
- **Alternatives considered**: Letting the assistant read and edit `engagement.md` directly.
  That is simpler, but it puts the real name into the conversation on every run.

## R8. Recording model-use restrictions

- **Decision**: Add `model_use_notes: ""` to the engagement record, after `model_use`, and
  to the front matter of `scope.md`. Also add a `Restrictions:` line to the Model use
  section of `scope.md`. `model-use --set <value> [--notes <text>]` replaces the `model_use:`
  and `model_use_notes:` lines (keeping any trailing comment), adds a missing
  `model_use_notes:` line after `model_use:`, and rewrites the "Current policy" and
  "Restrictions" lines in `scope.md`. Only the consultant's stated values are written.
  Declining to settle the policy writes nothing (US2-3).
- **Rationale**: FR-005 requires the specific restrictions to be stored in both places. A
  free-text note is enough for Phase 1. `ingest` still uses the per-source
  `restricted: true` flag.
- **Alternatives considered**: A structured list of restriction rules. Too early: no
  consumer reads them yet, and the agreements vary per client.

## R9. Assigning IDs

- **Decision**: For each prefix (`Q`, `H`, `A`), the next ID is one more than the highest
  number in **any** token matching `\b<P>-(\d{3,})\b` in the engagement's content markdown:
  every `*.md` under the canonical content folders except `10-sources/` and `_templates/`.
  IDs are zero-padded to three digits and grow to four after `999`. Duplicates and malformed
  headings (for example `## Q-3:` or a heading ID that differs from the `id` field) are
  reported, never fixed (spec edge case).
- **Rationale**: Counting every mention, not just headings, means an entry deleted by hand
  can't have its number reused while an observation, a log line or the changelog still
  refers to it (Principle V). The script only outputs numbers.
- **Alternatives considered**: Highest heading in the collection file only. Simpler, but it
  reuses numbers after a hand deletion.

## R10. Revision model: new versions, and changes inside the session

- **Decision**:
  - An item is **existing** if it was already in the files when the session started. Items
    written during the current session, while still `proposed`, may be amended in place
    until the session ends. They are part of the draft being agreed, and nothing else
    relies on them yet.
  - Changing the claim of an existing item creates a new item with the next free ID,
    `status: proposed`, `supersedes: ["<old ID>"]`, and `change_reason` and `change_trigger`
    set. The old item is untouched (FR-024).
  - Approving the new version sets it to `active`, sets the old item to `superseded`, copies
    `change_reason` and `change_trigger` onto the old item, and logs one `supersede` event.
  - Two new standard fields, added to **every** template: `change_reason` (one line) and
    `change_trigger` (`new-evidence` | `client-feedback` | `rethinking`). They hold the
    reason and trigger of the most recent supersede or reject event that touched the
    object. The full history is in the changelog.
- **Rationale**: Without the in-session rule, every edit during the first review (US3)
  would create a new version of an item nobody has seen yet, filling the charter with
  supersede chains. The two fields keep the reason on the item itself, as FR-024 and FR-026
  require ("keeps its text and the reason"), and give `record-change` the same fields for
  every object type (FR-030).
- **Alternatives considered**: Logging the pending revision in the changelog straight
  away. That would make `what-changed` report revisions the consultant hasn't approved.
  Putting the reason in the body text isn't machine-readable for `what-changed` or for
  later checks against negative lessons.

## R11. Clarifications

- **Decision**: A wording change that keeps the claim (FR-025) edits the title or body in
  place. The `clarify` changelog event keeps the previous wording in a quoted block. No new
  ID is created, and the item's status doesn't change. The `clarifies` field stays for
  separate objects that refine another one (for example, a follow-up observation).
- **Rationale**: The spec says "not a new version". The framework design treats a
  clarification as "an event recorded against an existing object". The previous wording is
  kept, so nothing is lost (Principle VI).
- **Alternatives considered**: A new object with `clarifies: [<ID>]`, which is too heavy
  for a wording fix and is what the spec rules out.

## R12. Changelog entry format

- **Decision**: Keep the five-field line that feature 001 seeded, and add an optional
  quoted block underneath:

  ~~~text
  YYYY-MM-DD · <subject> · <event> · <reason> · <trigger>
  > <optional detail: previous text, or what moved>
  ~~~

  - `<subject>` is an item ID (`A-001`), a pair for versions or moves (`H-002 → H-004`,
    `H-003: Q-002 → Q-005`), or a scope section (`scope/Timeline`).
  - `<event>` is one of `supersede`, `correct`, `clarify`, `reject`, `scope-change`,
    `relink`, `model-use` or `approve-charter`.
  - `<trigger>` is `new evidence`, `client feedback` or `rethinking`. The two events that
    don't need a trigger, `model-use` and `approve-charter`, write `-` instead.
  - The quoted block is required for `clarify` and `scope-change`, where it holds the
    previous text.
  The full rules are in [contracts/change-convention.md](contracts/change-convention.md).
- **Rationale**: Existing engagements already carry the five-field guidance, so new entries
  stay readable next to it. The quoted block holds the multi-line previous text that FR-027
  requires without breaking the one-line-per-event scan that `what-changed` will use.
  Logging `model-use` and `approve-charter` gives `what-changed` the two stage-1 milestones.
- **Alternatives considered**: One YAML block per event, which is heavier to read and to
  write by hand. A separate scope-history file, which would put the change log in two
  places.

## R13. Where the shared convention is written (FR-030)

- **Decision**: The convention for record-change events is written once, as
  `skills/charter/reference/change-convention.md`, and mirrored as the design contract in
  `contracts/change-convention.md`. The changelog seed's guidance is updated to the same
  format. When `record-change` is built, it ships an identical copy, and a test asserts the
  copies are byte-identical.
- **Rationale**: Skills are copied as self-contained folders, so a skill cannot reliably
  read another skill's files. A byte-identity test stops the copies drifting apart.
- **Alternatives considered**: A `_templates/change-event.md`. `_templates/` holds one
  template per object type, the 001 tests check exactly that set, and a change event is not
  an object with an ID. A framework document outside the skills isn't copied into the
  engagement.

## R14. Hypotheses state confirm and reject conditions as fields

- **Decision**: Add `confirm_if: ""` and `reject_if: ""` to the hypothesis template. The
  body keeps the one-sentence hypothesis.
- **Rationale**: FR-015 requires both. FR-031 and the gap check need to detect "no rejection
  condition", which a script can only do from a field. `test-hypothesis` (Phase 2) will read
  the same fields.
- **Alternatives considered**: Headings in the body (`**Confirms:**`, `**Rejects:**`),
  which are easy to break with hand edits and harder to check.

## R15. Shape of `scope.md`, `stakeholders.md` and `lenses.md`

- **Decision**:
  - `scope.md` front matter gains `model_use_notes`, `charter_status` (`draft` |
    `approved`), `approved_on` and `approved_by`. The body gains `### In scope` and
    `### Out of scope` under Boundaries, and a `## Constraints` section (budget, timeline,
    technology, politics) before Model use. The seed guidance sentence under a heading is
    replaced by the content when that section is first filled.
  - Stakeholders: one table row each. A literal `|` in a cell is escaped as `\|`. Interview
    status is one of `not yet interviewed` (default), `scheduled` or `interviewed`.
  - Lenses and criteria: one bullet each, `- **<Name>**: <one-line description>`, under
    `## Lenses` or `## Evaluation criteria`.
  - For engagements created before this feature, the skill adds missing headings and front
    matter fields the first time it writes. Seed files are never refreshed (001 FR-023), so
    the skill has to handle both shapes.
- **Rationale**: FR-008 requires the interview to cover constraints, and the seed `scope.md`
  had nowhere to put them. Approval needs a place in `scope.md` (FR-035, spec assumption).
  A fixed bullet format lets later requests name a lens and lets the script count them.
- **Alternatives considered**: Recording constraints as assumptions. Constraints are given
  facts, not assumptions taken without evidence.

## R16. How the skill picks its mode

- **Decision**: `status` reports `charter_state`:
  - `empty`: no Q, H or A entries, and every scope section still holds its seed guidance.
    The skill runs the full interview.
  - `draft`: something exists and `charter_status` is not `approved`. The skill runs
    revision mode, then review.
  - `approved`: the charter has been approved. The skill runs revision mode.
  Revision mode summarizes what exists and asks what has changed (US4-2). If topics are
  still missing in `draft`, it offers to continue the interview for those topics only.
- **Rationale**: FR-003 says revision mode whenever a charter exists. An interrupted first
  session (US1-6) then resumes where it stopped, without asking again.

## R17. Interview design

- **Decision**:
  1. Run `status`. Stop if there is no engagement.
  2. Model use first: if `unconfirmed`, ask (FR-004). If `restricted` or `unconfirmed`, give
     the paste reminder once (FR-007).
  3. Parse anything the consultant gave up front into topics (FR-011).
  4. Cover topics in a fixed order: objectives → boundaries → deliverables → timeline →
     constraints → key questions → hunches → assumptions → stakeholders → lenses and
     criteria. A topic already covered by an earlier answer is shown back for confirmation
     (FR-010).
  5. Save each topic as soon as it is confirmed (FR-022), then run `check`.
  6. Gap check, and up to five suggestions, each kept or discarded (FR-031, FR-032).
  7. Review and approval (US3).
  8. End summary (FR-039).
  Questions come before hunches, so each hunch can be tied to a question as it is
  recorded (FR-015). A hunch that fits no question gets an offered question (edge case).
  The starting set of lenses is cost, risk, customer experience and operating model
  (FR-012).
- **Rationale**: This mirrors the order in the framework design (scope → questions →
  hunches → constraints) and keeps the minimum for a draft (objectives and one question,
  FR-009) early in the session.

## R18. Approving the charter

- **Decision**: "Approve all" sets every `proposed` Q, H and A to `active`. This includes
  pending new versions, which are applied as in R10. It then sets
  `charter_status: approved`, `approved_on: <today>` and `approved_by`, and logs
  `approve-charter`. The approver defaults to `lead_consultant` from `status`, and the
  consultant is asked to confirm it. If `model_use` is `unconfirmed`, items may still be
  approved one by one, but `charter_status` stays `draft` and the skill says why (FR-035).
  A later approval updates `approved_on` and `approved_by`. Revisions after approval don't
  reset `charter_status`. The summary shows how many items have been proposed since the
  last approval.
- **Rationale**: Approval is a record of the consultant's decision, not a lock. Resetting to
  `draft` on every weekly revision would make the state meaningless.

## R19. Objects that link to a changed item (FR-029)

- **Decision**: `refs <ID>…` scans every Cairn object outside `10-sources/` and `_templates/`
  (charter entries, `_inbox/`, `20-research/` to `50-options/`, decisions and lessons). It
  reports each object whose fields contain the ID, as `{id, field, file}`. Each object's own
  `id` field and the changelog are excluded. When a question is superseded, the skill lists
  its active and proposed hypotheses and asks which should move. A move changes the
  hypothesis's `question`, adds it to the new question's `hypotheses`, removes it from the
  old question's list, and logs `relink`. The hypothesis's claim is unchanged.
- **Rationale**: Removing the moved hypothesis from the old question keeps SC-004 strict
  (links agree in both directions), and the changelog keeps the history. Body text isn't
  scanned, because links are IDs in fields (Principle V).

## R20. Testing strategy

- **Decision**: Three levels:
  1. **Automated, deterministic (pytest, always run).**
     - *Script unit tests*: the parser (front matter, entries, list forms, malformed input),
       ID assignment (gaps, hand edits, IDs mentioned elsewhere), link checks, gap detection,
       `refs`, `model-use` edits (comments kept, missing field added), the real-name leak
       check, and the `10-sources/` exclusion. For the exclusion test, `10-sources/` holds
       a canary file with its read permission removed, so any attempt to open it fails.
     - *Asset tests*: the `charter` skill ships with valid `SKILL.md` front matter. `init`
       copies it, `refresh` adds it to an engagement created without it, and every template
       has the new standard fields. The `check` command passes on golden synthetic charters
       (drafted, approved, revised) and fails on broken ones.
     - *Updated 001 tests*: the bundled-skill count is now 1, the README lists `charter`,
       and the "no skills bundled" case moves to a fixture asset set.
  2. **Skill evaluation (opt-in, `CAIRN_SKILL_EVAL=1`, needs the `claude` CLI).** Scripted
     scenarios for US1–US5 and the edge cases. Each runs `claude -p`, using `--resume` for
     multi-turn interviews, in a fresh synthetic engagement. It then asserts on the files
     with `check`, on before/after diffs (SC-006, SC-007) and on the tool-call transcript
     (SC-005, R6). These tests use synthetic data only and are skipped in normal runs
     because they call a live model.
  3. **Manual validation**: the quickstart walkthrough, and the Phase 1 trial engagement
     held locally for SC-001, SC-002 and SC-008. The trial engagement is never committed
     (Principle VIII).
- **Rationale**: The script and the bundled assets can be tested exactly. The interview
  depends on the model, so it is checked by scenario evaluation against the same `check`
  rules, plus human judgment for the time and quality criteria.
- **Alternatives considered**: Evaluation runs in CI. They cost money, are not
  deterministic, and need credentials. They can be added later if the skill changes often.

## R21. Skill front matter

- **Decision**:

  ~~~yaml
  name: charter
  description: "Frame or revise the engagement charter (scope, key questions, hypotheses, assumptions, stakeholders, lenses) by interviewing the consultant. Use at kickoff, or when the weekly steer changes questions, hypotheses or scope. Never reads client documents."
  argument-hint: "[anything you already know: objectives, deadlines, hunches…]"
  allowed-tools: Read, Edit, Write, Bash(python3 *charter.py *)
  ~~~

  Model invocation stays enabled, so "let's set up the charter" triggers the skill.
  `allowed-tools` pre-approves the script and file edits so the interview isn't interrupted
  by permission prompts. It doesn't restrict tools, which is why R6 does not rely on it.
- **Rationale**: The description doubles as the README's skill line (001 `bundled_skills`),
  so it says what the skill does in one sentence first. The description is one double-quoted
  line because `cairn`'s front matter reader (`textutil.read_front_matter`) only reads flat
  values. A folded `>-` value would show up in the engagement README as `>-`.

## R22. Framework version

- **Decision**: Bump `cairn.__version__` from `0.1.0` to `0.2.0`. The changes add a skill and
  change the templates (new fields), which is a minor framework change. `cairn refresh` then
  brings existing engagements the new templates and the skill. Seed changes apply to new
  engagements only, and the skill fills in missing seed fields itself (R15).
- **Rationale**: Feature 001's refresh only updates when the running version is newer.
