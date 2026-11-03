# Feature Specification: Engagement Initialization

**Feature Branch**: `001-engagement-init`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Using this description to help scope the feature, I want to create a script to initialize a new engagement. The implementation in this framework should be set up to help establish projects (an engagement) for analyzing the engagement with a client. This would be similar to what is done in the 'speckit init' utility to set up a new project."

## Clarifications

### Session 2026-11-03

- Q: Should this feature also include a first, working version of the `charter` skill? → A: No. `charter` is its own feature. This feature makes every bundled skill available, and `charter` is confirmed when it ships.
- Q: When the consultant gives a code name, should the client's real name still be stored in the engagement record? → A: Only if the consultant gives it. When a code name is used, the real name is optional. If it's left out, it appears in no generated file. If it's given, it appears only in the engagement record.
- Q: If the new engagement is created inside an existing git repository, what should the command do about version control? → A: It doesn't create a repository and doesn't commit. It leaves the files uncommitted, says so in the summary, and warns if that repository has a remote.
- Q: During refresh, should a skill the consultant edited be protected the same way as an edited template? → A: Yes. Edits are detected, the consultant confirms before each one is replaced, and their version is kept as a backup.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a new engagement workspace (Priority: P1)

A consultant starting work with a client runs a single initialization command, gives the
engagement a name and the client's name (or a code name), and gets a new engagement folder
that already follows the Cairn canonical layout. The folder contains every standard
sub-folder, a README explaining how to use it, empty charter files, an empty source
catalogue, empty decision/lesson/change logs, and one template per object type. The
consultant can immediately start the `charter` interview and drop original files into the
raw sources folder.

**Why this priority**: Every other Cairn skill assumes this layout exists. Without a
consistent, correct starting folder, skills cannot find or write their files, and
engagements drift apart in structure, which breaks the Phase 1 trial.

**Independent Test**: Run initialization into an empty location with a synthetic client
name, then compare the result against the canonical layout in the constitution: every
folder and seed file is present, every seed file is plain markdown with valid front matter,
and no numbered objects (sources, observations, findings, etc.) exist yet.

**Acceptance Scenarios**:

1. **Given** an empty or non-existent target location, **When** the consultant initializes an
   engagement named "Fulfillment Review" for client "Acme", **Then** a folder named
   `acme-fulfillment-review` is created containing `_inbox/`, `_templates/`, `00-charter/`,
   `10-sources/raw/`, `10-sources/extracted/`, `20-research/`, `30-observations/`,
   `40-synthesis/findings/`, `40-synthesis/issues/`, `40-synthesis/opportunities/`,
   `50-options/`, `60-log/`, `70-views/` and `80-deliverables/`.
2. **Given** a newly created engagement, **When** the consultant opens it, **Then** it contains
   a `README.md`, an engagement record holding the engagement's identity and settings,
   the six charter files (`scope.md`, `questions.md`, `hypotheses.md`, `assumptions.md`,
   `stakeholders.md`, `lenses.md`), `10-sources/index.md`, and `60-log/decisions.md`,
   `lessons.md` and `changelog.md`, each with headings and front matter but no objects.
3. **Given** a newly created engagement, **When** the consultant looks in `_templates/`,
   **Then** there is one template for each object type (source, observation, question,
   hypothesis, assumption, research result, finding, issue, opportunity, option, decision,
   lesson), each defaulting to status `proposed` and audience `internal`.
4. **Given** the consultant did not supply the engagement or client name on the command,
   **When** initialization runs, **Then** it asks for each missing required value before
   creating anything.
5. **Given** the consultant did not opt out of version control, **When** initialization
   completes, **Then** the engagement folder is under local version control, has an initial
   snapshot of all created files, and has no remote configured.
6. **Given** initialization completed, **When** the summary is shown, **Then** it lists what
   was created and the next steps (record the model-use policy, run `charter`, add sources
   to `10-sources/raw/`).

---

### User Story 2 - Safe and confidential by default (Priority: P1)

A consultant initializes an engagement without having to remember the confidentiality
rules. Initialization refuses to place an engagement inside the Cairn framework repository,
refuses to overwrite an existing folder's content, and records the client's model-use
policy as "unconfirmed" until the consultant sets it, so no later skill assumes that
sending client documents to an external AI service is allowed.

**Why this priority**: Confidentiality is a non-negotiable principle (VIII). Initialization
is the first and cheapest point to stop client data from ending up in the wrong place or
being sent to a model without permission.

**Independent Test**: Attempt initialization (a) inside the framework repository, (b) into
a non-empty folder, and (c) without stating a model-use policy; confirm (a) and (b) are
refused with a clear explanation and no files written, and (c) produces an engagement
whose record shows the policy as unconfirmed.

**Acceptance Scenarios**:

1. **Given** a target location inside the Cairn framework repository, **When** the
   consultant runs initialization, **Then** it stops with an explanation and creates nothing.
2. **Given** a target folder that already contains files, **When** the consultant runs
   initialization without explicitly asking to initialize into the existing folder, **Then**
   it stops, lists the conflict, and creates nothing.
3. **Given** the consultant explicitly asks to initialize into an existing non-empty folder,
   **When** initialization runs, **Then** it adds only missing folders and files, leaves
   every existing file untouched, and reports which files it skipped.
4. **Given** the consultant does not state the client's model-use policy, **When**
   initialization completes, **Then** the engagement record and `00-charter/scope.md` show
   the policy as `unconfirmed`, and the README and summary flag it as needing a decision
   before any source is ingested.
5. **Given** the consultant states the model-use policy (allowed, restricted, or
   unconfirmed) at initialization, **When** initialization completes, **Then** the stated
   value is recorded in the engagement record.
6. **Given** the client's real name must not appear in folder names on shared storage,
   **When** the consultant supplies a code name, **Then** the folder name and engagement
   identifier use the code name only. If the consultant also supplies the real name, it
   appears only in the engagement record. If they don't, no generated file contains it.

---

### User Story 3 - Agent-ready from the first minute (Priority: P2)

A consultant opens the new engagement folder in their editor with their AI assistant and
can invoke Cairn skills (starting with `charter`) right away, without copying files or
configuring anything by hand.

**Why this priority**: The framework's value comes from the skills. If making them
available is a manual step, consultants will skip it or do it inconsistently, but the
folder layout (Story 1) is still useful on its own for hand-written work.

**Independent Test**: Bundle a synthetic test skill with the framework, initialize a
synthetic engagement, open it with the supported AI assistant, and invoke that skill; it is
found without any setup. The `charter` skill itself is delivered and checked by its own
feature.

**Acceptance Scenarios**:

1. **Given** a newly created engagement, **When** the consultant asks their AI assistant to
   run any skill bundled with the framework (for example `charter`, once it ships) from
   inside the engagement folder, **Then** the skill is available without further setup.
2. **Given** a newly created engagement, **When** the consultant inspects the engagement
   record, **Then** it shows which framework version provided the templates and skills.

---

### User Story 4 - Refresh framework files in an existing engagement (Priority: P3)

Mid-engagement, the framework gains an improved template or a new skill. The consultant
refreshes the engagement's framework-provided files to the current framework version
without any risk to the engagement's sources, objects, charter or logs.

**Why this priority**: Engagements last about four weeks and the framework is being built
in phases, so skills will change during live engagements. It is less urgent than creating
engagements correctly in the first place.

**Independent Test**: Initialize a synthetic engagement, add sample content to every
content folder, change the framework's templates, run refresh, and confirm that only
framework-provided files changed and every content file is byte-for-byte identical.

**Acceptance Scenarios**:

1. **Given** an existing engagement created with an older framework version, **When** the
   consultant refreshes it, **Then** templates and skills are updated, the recorded framework
   version is updated, and a list of changed files is shown.
   Skills only change when the engagement is refreshed, never because the framework changed.
2. **Given** the consultant has edited a template or skill in their engagement, **When** they
   refresh, **Then** that file is not replaced without the consultant's confirmation, and the
   consultant's version is kept as a backup if they confirm.
3. **Given** any engagement, **When** refresh runs, **Then** nothing in `10-sources/`, the
   charter, the object folders, `60-log/`, `70-views/`, `80-deliverables/` or `_inbox/` is
   created, changed or deleted.
4. **Given** an engagement created by a newer framework version than the one running the
   refresh, **When** refresh is attempted, **Then** it stops and explains the mismatch.

---

### Edge Cases

- Engagement or client names with spaces, capitals, accents or punctuation are turned into
  a safe, lowercase, hyphenated folder name; the names as typed are kept in the engagement
  record (subject to FR-016 when a code name is used).
- The target folder name already exists for the same client (for example, a second
  engagement): initialization refuses rather than merging, and suggests a distinct name.
- The target is inside another engagement folder: initialization refuses, since nested
  engagements would confuse ID assignment and confidentiality boundaries.
- The consultant lacks permission to write to the target location: initialization stops
  before creating anything and says why.
- Initialization is interrupted or fails partway: it removes only the files and folders it
  created in that run (never pre-existing ones) and reports the failure.
- The framework's own templates or skills are missing or incomplete: initialization stops
  and reports which assets are missing instead of creating a partial engagement.
- Refresh is pointed at a folder that is not a Cairn engagement (no engagement record):
  it refuses.
- The target is inside an existing version-control repository: no new repository and no
  commit are made, the summary says the files are uncommitted, and it warns if that
  repository has a remote, since pushing it would send client material off the machine.

## Requirements *(mandatory)*

### Functional Requirements

**Creating an engagement**

- **FR-001**: The framework MUST provide a single command that creates a new engagement
  folder at a location the consultant chooses, defaulting to the current working location.
- **FR-002**: The command MUST require an engagement name and at least one of a client name
  or client code name, and MUST derive the folder name as `<client>-<engagement>` in lowercase hyphenated
  form unless the consultant supplies a folder name explicitly.
- **FR-003**: The command MUST accept all inputs as arguments for unattended use, and MUST
  prompt for any missing required input when run interactively.
- **FR-004**: The command MUST create every folder in the constitution's canonical
  engagement layout, and no others.
- **FR-005**: The command MUST create seed files: `README.md`; an engagement record; the six
  charter files in `00-charter/`; `10-sources/index.md`; and `decisions.md`, `lessons.md` and
  `changelog.md` in `60-log/`. Seed files MUST contain headings, guidance and front matter
  only, and no objects.
- **FR-006**: The command MUST populate `_templates/` with one template per object type,
  taken from the framework's master templates. Each template MUST include the standard
  fields (ID, type, status, origin, confidence with reason, audience, links, created date)
  and MUST default to status `proposed` and audience `internal`.
- **FR-007**: The command MUST NOT create any numbered object, so the first ID of every type
  assigned in the engagement is `-001`.
- **FR-008**: The engagement record MUST capture: engagement name, client name or code
  name, lead consultant, team members (optional), start date, creation date, framework
  version, and model-use policy.
- **FR-009**: Every file the command creates MUST be plain markdown, with YAML front matter
  where the file describes an object or the engagement. The command MUST NOT create a
  database, server, or proprietary-format file as a system of record.
- **FR-010**: On success, the command MUST print a summary of what it created and the
  next steps: confirm the model-use policy, run `charter`, and add originals to
  `10-sources/raw/`.
- **FR-011**: The README MUST explain the folder layout, the status and provenance rules,
  the daily triage habit, and the skills available, so a new team member can work in the
  folder without other documentation.

**Safety and confidentiality**

- **FR-012**: The command MUST refuse to create an engagement anywhere inside the Cairn
  framework repository, or inside another engagement folder.
- **FR-013**: The command MUST refuse to write into a non-empty folder unless the consultant
  explicitly asks to initialize into an existing folder. In that case it MUST add only
  missing items, MUST NOT overwrite, rename or delete any existing file, and MUST report
  every file it skipped.
- **FR-014**: The command MUST never modify, move or delete anything in `10-sources/raw/`.
- **FR-015**: The model-use policy MUST be one of `allowed`, `restricted` or `unconfirmed`,
  MUST default to `unconfirmed`, and MUST be shown in both the engagement record and
  `00-charter/scope.md`. When it is `unconfirmed`, the README and the summary MUST say that
  it must be set before any source is ingested.
- **FR-016**: The command MUST support a client code name so that the real client name does
  not appear in the folder name or engagement identifier. When a code name is given, the
  real client name MUST be optional. If it is omitted, it MUST NOT appear in any generated
  file, folder name or version-control message. If it is given, it MUST appear only in the
  engagement record.
- **FR-017**: If the command fails partway, it MUST remove only what it created during that
  run, leave pre-existing content untouched, and report what failed.
- **FR-018**: The command MUST NOT send any engagement information to any external service,
  and MUST NOT configure any remote destination for the engagement.

**Agent readiness and version control**

- **FR-019**: The command MUST copy the Cairn skills into the engagement folder, in the
  location the consultant's AI assistant looks for project skills, so the engagement is
  self-contained and its skills stay at the framework version that created it until refreshed.
- **FR-020**: The command MUST record the framework version used to create the engagement
  in the engagement record.
- **FR-021**: By default, the command MUST set up local version control for the engagement
  folder and record an initial snapshot of everything it created. All engagement content,
  including raw originals in `10-sources/raw/`, MUST be tracked. The consultant MUST be able
  to opt out at initialization. If the target is already inside an existing repository, the
  command MUST NOT create a new one and MUST NOT commit anything. It MUST leave the created
  files uncommitted, say so in the summary, and warn if that repository has a remote
  configured.

**Refreshing an existing engagement**

- **FR-022**: The framework MUST provide a refresh mode that updates framework-provided files
  (templates and skills) in an existing engagement to the
  current framework version and updates the recorded framework version.
- **FR-023**: Refresh MUST NOT create, change or delete any file outside framework-provided
  areas. In particular, it MUST NOT touch sources, charter files, objects, logs, views,
  deliverables or the inbox.
- **FR-024**: Refresh MUST detect framework-provided files (templates and skills) the
  consultant has edited, ask for confirmation before replacing each one, and keep the
  consultant's version as a backup when replacing.
- **FR-025**: Refresh MUST refuse to run on a folder that has no engagement record, or on an
  engagement created by a newer framework version than the one running.

### Key Entities

- **Engagement**: One client project, represented by one folder. Identified by a
  lowercase hyphenated name derived from client (or code name) and engagement name.
  Contains all sources, objects and logs for that project, and nothing from other
  engagements.
- **Engagement record**: The single file that identifies the engagement and holds its
  settings: names, lead consultant, team, dates, framework version and model-use policy.
  Later skills read it to check, for example, whether ingestion is permitted.
- **Canonical layout**: The fixed set of folders defined in the constitution. Changing it
  requires a constitution amendment.
- **Framework assets**: The master templates (one per object type) and skills shipped with
  the framework. They are copied into each engagement's `_templates/` and skills location
  and carry a framework version.
- **Model-use policy**: What the client agreement allows to be sent to external AI services:
  `allowed`, `restricted` or `unconfirmed`. Recorded at initialization and confirmed in the
  charter.
- **Seed files**: The README, charter files, source catalogue and log files created empty at
  initialization so skills have fixed places to write to.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A consultant can go from nothing to an engagement ready for the `charter`
  interview in under 2 minutes, including answering prompts.
- **SC-002**: 100% of engagements created by the command match the canonical layout exactly,
  with no missing or extra folders, as confirmed by an automated layout check.
- **SC-003**: 100% of attempts to create an engagement inside the framework repository or
  inside another engagement are refused, with no files written.
- **SC-004**: Initializing into an existing folder, or refreshing an engagement, changes
  zero existing content files, as confirmed by comparing file contents before and after.
- **SC-005**: In a fresh engagement, the consultant can invoke every skill bundled with the
  framework on the first attempt with no manual setup. This is checked here with a
  synthetic test skill, and again for `charter` when that feature ships.
- **SC-006**: 100% of new engagements show a model-use policy in the engagement record, and
  every engagement where it was not stated shows `unconfirmed`.
- **SC-007**: A team member new to Cairn can, using only the engagement README, correctly
  say where to put a new original document and where agent output awaits review in under
  10 minutes.

## Assumptions

- Users are consultants and analysts at the firm (a team of 1–3 analysts plus the lead
  consultant per engagement) working on their own workstations, primarily macOS and Linux.
- Engagements are created on local or firm-approved storage chosen by the consultant; the
  command does not decide where client data may be stored.
- Initialization only prepares the folder. Filling in scope, questions, hypotheses and
  stakeholders is the job of the `charter` skill, and is out of scope here.
- The command records the model-use policy but does not enforce it; enforcement (refusing
  restricted sources) belongs to `ingest`.
- Master templates for every object type are part of the framework and are delivered as part
  of this feature where they do not yet exist.
- Skills not yet built, including the Phase 1 skills such as `charter`, are simply absent
  from new engagements; refresh adds them as they become available. This feature does not
  deliver any skill.
- Archiving, returning or deleting raw sources at engagement close is out of scope and will
  be handled by a later close-out feature. Because raw originals are tracked in version
  history (FR-021), that feature must also deal with removing them from history, or
  disposing of the whole history, when the client agreement requires deletion.
- Raw originals are tracked in version history because, at about 10–20 sources per
  engagement, the size is manageable, and keeping originals with the work that cites them
  supports Principle II (originals are the final arbiter).
- Copied skills are the ones for the consultant's supported AI assistant (Claude Code
  initially); supporting other assistants is out of scope for this feature.
- A separate "check engagement health" command (similar to `specify check`) is out of scope;
  the layout check used for SC-002 may be reused later for that.
- All test engagements used to validate this feature are synthetic; no real client data is
  used in the framework repository (Principle VIII).
