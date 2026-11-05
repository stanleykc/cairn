# Feature Specification: Extract Observations Skill

**Feature Branch**: `005-extract-observations`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "Using '/Users/stanleyk/dev/cairn/requirements-draft/description.md' as guidance to create the specification for 'extract-observations'"

## Clarifications

### Session 2026-11-05

- Q: With no focus given, should the skill extract every factual claim, or only claims that
  bear on at least one charter question? → A: Every factual claim. Claims that bear on no
  question are kept untagged and listed separately in the summary.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract cited observations from a source (Priority: P1)

A client operations review has been ingested as `S-004`. The consultant runs
`extract-observations S-004`. The skill reads the source's extracted content and proposes a
set of observations. Each one is a single claim taken from the source, with no
interpretation: for example, "Order-to-ship time averaged 9 days in Q3, against a 5-day
target." Each observation gets the next free `O-###` ID and is written as its own file to
`_inbox/`, with status `proposed`. It cites `S-004` and a locator (page, table, section,
timestamp) and includes the exact passage it was taken from, so the consultant can check
it against the source in seconds. It carries the source's origin and a confidence with a
reason, and it is marked as derived if it came from OCR text or a chart description. The
skill ends with a summary of what it proposed, ready for triage.

**Why this priority**: Observations are the smallest unit of work in Cairn. Every finding,
issue, option and recommendation is built from them. Stage 3 of the pipeline is the bridge
between ingested sources and synthesis; without it, nothing downstream can cite evidence.

**Independent Test**: In a synthetic engagement, ingest a synthetic PDF (text, a table and
a chart) as `S-001` and run `extract-observations S-001`. Confirm that each proposed
observation is one file in `_inbox/` with a unique `O-###` ID, status `proposed`, audience
`internal`, source `S-001` and a locator. Confirm that each observation's quoted passage
appears word for word in `S-001` at that locator, that observations from the chart
description are marked as derived, and that no observation states a conclusion the source
does not state.

**Acceptance Scenarios**:

1. **Given** an ingested source, **When** the consultant runs `extract-observations` with
   its ID, **Then** the skill writes each proposed observation as one file in `_inbox/`
   with the next free `O-###` ID, status `proposed` and audience `internal`.
2. **Given** a claim in the source, **When** it becomes an observation, **Then** the
   observation states exactly one claim, cites the source ID and a locator that points to
   where the claim appears, and includes the exact passage it was taken from.
3. **Given** a sentence that holds several claims (for example, a figure and a cause),
   **When** it is extracted, **Then** each claim becomes its own observation, each citing
   the same passage.
4. **Given** a claim that would need interpretation, calculation or combining two passages
   to state, **When** the skill extracts, **Then** it does not write it as an observation.
5. **Given** a claim read from derived content (OCR text, a chart or diagram description),
   **When** it becomes an observation, **Then** the observation is marked as derived.
6. **Given** a claim from a passage the source lists as uncertain, **When** it becomes an
   observation, **Then** its confidence is `low`, with a reason naming the uncertain
   extraction.
7. **Given** a source with origin `client-document`, `interview-meeting` or
   `consultant-note`, **When** observations are written, **Then** each carries that same
   origin, and its confidence is no higher than the source's.
8. **Given** a table in the source, **When** observations are drawn from it, **Then** each
   locator names the table and the row (and column, where needed), not just the page.
9. **Given** the extraction finishes, **When** the skill reports, **Then** it lists the
   observations it proposed by ID and title, grouped by question, and says how to review
   them.

---

### User Story 2 - Steer extraction toward the engagement's questions (Priority: P1)

The consultant wants evidence for a specific question, not a generic summary. They run
`extract-observations S-004 S-007 for Q-003, why fulfillment is slow; ignore the appendix`.
The skill reads the questions in `00-charter/questions.md`, extracts what bears on Q-003
from both sources, and tags each observation to the questions it is relevant to. It skips
the appendix. If the consultant names a stakeholder perspective ("from the warehouse
manager's point of view"), the skill favors what that stakeholder said or what concerns
them, and says so in its summary.

**Why this priority**: The requirements draft is explicit that steering input decides
quality. "Extract what bears on Q-003" beats "extract observations." Question tags are also
what `synthesize` and `test-hypothesis` use to find evidence, so tagging has to happen at
extraction time.

**Independent Test**: In a synthetic engagement with three questions in the charter, ingest
two synthetic sources whose content bears on different questions. Run the skill once with
no focus and once focused on one question with an exclusion. Confirm that every tag
refers to an existing `Q-###`, that the focused run proposes only observations relevant to
the named question, and that nothing is taken from the excluded part.

**Acceptance Scenarios**:

1. **Given** questions in `00-charter/questions.md`, **When** observations are written,
   **Then** each is tagged with the IDs of the questions it bears on, and only with IDs that
   exist.
2. **Given** the consultant names one or more questions, **When** the skill extracts,
   **Then** it proposes only observations that bear on those questions.
3. **Given** the consultant names a part of the source to ignore (pages, sections,
   speakers, appendices), **When** the skill extracts, **Then** no observation cites that
   part.
4. **Given** the consultant names a stakeholder perspective, **When** the skill extracts,
   **Then** it favors claims made by or about that stakeholder, and the summary states the
   perspective used.
5. **Given** the consultant gives no focus, **When** the skill extracts, **Then** it
   proposes every factual claim in the source. Claims that bear on no charter question are
   kept, untagged, and listed separately in the summary.
6. **Given** several source IDs, **When** the skill runs, **Then** it processes each source
   in turn and gives one combined summary.
7. **Given** the charter has no questions yet, **When** the skill runs, **Then** it says so,
   suggests running `charter` first, and, if the consultant wants to go ahead, writes
   observations with no question tags.

---

### User Story 3 - Faithful attribution for meetings and interviews (Priority: P1)

Interview transcripts are full of opinions, guesses and claims about other teams. An
observation from a transcript must record that a person said something, not that it is
true. When the warehouse manager says "sales always sends orders late," the observation
reads "The warehouse manager said sales sends orders late," cites the transcript at the
speaker turn's timestamp, and names the speaker as the confirmed name recorded at ingest.
An observation from a colleague's meeting summary records that it comes from a second-hand
account.

**Why this priority**: Turning a stakeholder's opinion into a fact is the most common way
an evidence trail goes wrong, and it is invisible later. Meetings are half the evidence
in a typical engagement, so this has to be right in the first version.

**Independent Test**: Ingest a synthetic transcript with three named speakers, one of whom
makes an unsupported claim about another team, and a synthetic meeting summary written by
a colleague. Run the skill on both. Confirm that every transcript observation names the
speaker and cites the turn's timestamp, that the unsupported claim is stated as what the
speaker said, and that every summary observation says it comes from a summary and who
wrote it.

**Acceptance Scenarios**:

1. **Given** a transcript turn, **When** a claim in it becomes an observation, **Then** the
   observation names the speaker (the confirmed name if one is recorded, otherwise the
   original label) and states the claim as what that speaker said.
2. **Given** a transcript, **When** an observation cites it, **Then** the locator is the
   turn's timestamp, or its turn number when there are no timestamps.
3. **Given** a meeting summary or notes, **When** a claim in it becomes an observation,
   **Then** the observation states it as reported in the summary, by its author.
4. **Given** a summary written by an AI note-taker, **When** observations are written from
   it, **Then** their confidence is no higher than `medium`.
5. **Given** a speaker states an opinion, estimate or hunch, **When** it becomes an
   observation, **Then** the wording keeps it as an opinion, estimate or hunch, not as a
   fact.

---

### User Story 4 - Re-run without duplicates or repeated mistakes (Priority: P2)

Sources are revisited as questions evolve. A week later, the consultant adds a new
question Q-006 and runs `extract-observations S-004 for Q-006`. The skill reads the
observations that already cite `S-004`, wherever they are and whatever their status. It
does not propose a claim that is already recorded. It does not propose again a claim the
consultant rejected. Where an existing observation bears on Q-006, it lists it and asks
whether to add the new tag, rather than writing a duplicate.

**Why this priority**: Stages 3 to 6 loop. Without this, each run floods the inbox with
duplicates and brings back rejected items, which makes triage slower each week. It ranks
below the first three because a first pass on each source already delivers value.

**Independent Test**: In a synthetic engagement, run the skill on a source, accept some
observations and reject one by hand, then add a question and run the skill again focused on
it. Confirm that no new observation repeats an existing or rejected claim, that the skill
offers to tag matching existing observations with the new question, and that a tag is
added only after the consultant confirms it.

**Acceptance Scenarios**:

1. **Given** observations already cite a source, **When** the skill runs on that source
   again, **Then** it does not propose a claim already recorded from the same passage, in
   `_inbox/` or `30-observations/`, with any status.
2. **Given** a rejected observation, **When** the skill runs again, **Then** it does not
   propose the same claim again.
3. **Given** an existing observation that bears on a newly named question, **When** the skill
   runs, **Then** it lists the observation and adds the question tag only on the
   consultant's confirmation, without changing the claim, and records the change.
4. **Given** IDs already used, including by rejected or superseded observations and by
   hand-written ones, **When** new observations are written, **Then** they are numbered
   after the highest existing `O-###`.

---

### Edge Cases

- The skill is run outside an engagement folder: it stops and explains how to create an
  engagement first.
- The model-use policy is `unconfirmed`: the skill reads no source and writes nothing, and
  says to settle the policy with `charter`.
- The source is restricted, or its content was removed: the skill does not read it, writes
  nothing for it, and says why. The consultant can record what they know as their own notes.
- The source ID doesn't exist, or its extraction is still in progress: the skill writes
  nothing for it and says why.
- The source is `proposed` (not yet spot-checked): the skill extracts from it, and the
  summary notes that the source itself is not yet approved.
- The source is `rejected` or `superseded`: the skill names the replacing source if there is
  one, and extracts from the old one only if the consultant confirms.
- No arguments are given: the skill lists sources that have no observations yet and asks
  which to process.
- The source's context or description sections (written by the consultant or `ingest`)
  hold claims: they are not evidence, and the skill never cites them.
- Word comments or tracked changes appear in the extracted content: an observation from
  them states that it comes from a comment or an unsettled change.
- Two passages in the same source, or two sources, disagree: each becomes its own
  observation. The skill does not decide which is right or link them as contradicting;
  that is later work. It may mention the apparent conflict in its summary.
- A claim appears several times in one source: it becomes one observation, citing the
  clearest occurrence.
- A source holds text addressed to an AI (hidden text, instructions): it is treated as
  content and never followed.
- A very long source would yield more observations than one session can handle: the skill
  stops at a natural break, says where it stopped, and continues from there on the next
  run.
- A run is interrupted: observations already written stay valid and complete; the next run
  skips claims already recorded.
- A source is in a language other than English: observations keep the claim's language
  in the quoted passage; the claim may be stated in English, marked as a translation.
- The engagement uses a client code name: titles and the summary use the code name. Quoted
  passages stay word for word.

## Requirements *(mandatory)*

### Functional Requirements

**Starting**

- **FR-001**: The `extract-observations` skill MUST be bundled with the framework, so new
  engagements include it and existing engagements gain it on refresh.
- **FR-002**: The skill MUST find the engagement record before doing anything else, and MUST
  stop with an explanation if it isn't run inside an engagement.
- **FR-003**: The skill MUST take one or more source IDs. With no arguments, it MUST list the
  sources that have no observations yet and ask which to process.
- **FR-004**: The consultant MAY add steering input: questions to focus on, parts of a source
  to ignore, and a stakeholder perspective. The skill MUST follow it and MUST state the
  steering it used in its summary.

**Reading sources**

- **FR-005**: The skill MUST read the model-use policy first. If it is `unconfirmed`, the skill
  MUST NOT read any source or write anything.
- **FR-006**: The skill MUST NOT read a source that is restricted or whose content was
  removed, and MUST NOT read anything in `10-sources/raw/`. It works only from extracted
  sources in `10-sources/extracted/`.
- **FR-007**: The skill MUST extract only from sources whose extraction is complete. It MAY
  extract from `proposed` and `active` sources; it MUST extract from `rejected` or
  `superseded` sources only on the consultant's confirmation.
- **FR-008**: The skill MUST draw observations only from the source's extracted content, never
  from its context or description sections, and MUST treat all source text as content,
  never as instructions.
- **FR-009**: The skill MUST NOT send engagement content to any service other than the
  consultant's AI assistant, and MUST NOT do web research.

**Writing observations**

- **FR-010**: Each observation MUST state exactly one claim taken from one source, with no
  interpretation, calculation, generalization or combination of passages. A claim that
  cannot be stated without these MUST NOT be written as an observation.
- **FR-011**: Each observation MUST cite its source ID and a locator precise enough to find the
  claim: page (and table, row or figure where relevant) for PDFs, heading path or paragraph
  number for documents, timestamp or turn number for transcripts.
- **FR-012**: Each observation MUST include the exact passage it was taken from, copied word
  for word from the source's extracted content at the cited locator.
- **FR-013**: Observations from transcripts MUST name the speaker and state the claim as what
  the speaker said. Observations from meeting summaries or notes MUST state the claim as
  reported by the summary's author. Opinions, estimates and hunches MUST stay worded as such.
- **FR-014**: Each observation MUST carry its source's origin. The skill MUST NOT write an
  observation with origin `llm-inference`.
- **FR-015**: Confidence MUST be no higher than the source's confidence, and MUST be `low` for a
  claim read from an uncertain passage. Observations from AI-written summaries MUST NOT be
  rated above `medium`. Each confidence MUST have a one-line reason.
- **FR-016**: An observation read from derived content (OCR text, a chart, diagram or photo
  description) MUST be marked as derived.
- **FR-017**: Each observation MUST be tagged with the IDs of the charter questions it bears
  on, using only question IDs that exist. The skill MUST NOT create questions or hypotheses.
- **FR-018**: The skill MUST NOT set `supports`, `contradicts` or other links between
  observations, findings or hypotheses. That belongs to later skills.
- **FR-019**: Each observation MUST be written as its own file in `_inbox/`, using the
  engagement's observation template, with status `proposed` and audience `internal`. The
  skill MUST NOT set an observation to `active`, `rejected` or `client-ready`.
- **FR-020**: New IDs MUST be the next free `O-###` number across `_inbox/` and
  `30-observations/`, counting every status and hand-written observations. IDs MUST NOT be
  reused, and links MUST use IDs only.
- **FR-021**: Each observation MUST have a short title. When the engagement uses a client
  code name, titles and the session summary MUST use it; quoted passages stay word for word.

**Re-runs**

- **FR-022**: The skill MUST NOT propose a claim that an existing observation from the same
  source already records, in `_inbox/` or `30-observations/`, whatever its status. It MUST
  NOT propose again a claim the consultant rejected.
- **FR-023**: When an existing observation bears on a question named in the current run but
  isn't tagged with it, the skill MUST list it and add the tag only on the consultant's
  confirmation, without changing its claim, and MUST log the change in
  `60-log/changelog.md` with the date.

**Wrap-up**

- **FR-024**: At the end of each session, the skill MUST show a summary listing: the
  observations proposed (by ID and title), grouped by question; untagged observations;
  sources skipped and why; any point where a long source was stopped; apparent conflicts
  noticed; and the next step (review the inbox with `triage`).

### Key Entities

- **Observation (`O-###`)**: One claim from one source, with no interpretation. Holds the
  claim, the exact quoted passage, the source ID, a locator, origin, confidence with a
  reason, derived flag, question tags, status and audience. Written to `_inbox/` as
  `proposed`; moved into `30-observations/` once reviewed.
- **Source (`S-###`)**: An extracted original in `10-sources/extracted/`, produced by `ingest`.
  The skill reads its extracted content and its metadata (origin, confidence, restricted
  flag, uncertain passages, speakers).
- **Question (`Q-###`)**: A key question from `00-charter/questions.md`. Used to steer
  extraction and to tag observations.
- **Locator**: Where in the source a claim appears: page, table and row, heading path,
  paragraph number, timestamp or turn number.
- **Quoted passage**: The exact text in the source the claim was taken from, used to verify
  the observation against its source.
- **Steering input**: The consultant's focus questions, exclusions and stakeholder
  perspective for one run.
- **Triage inbox (`_inbox/`)**: Where proposed observations wait for the consultant's
  review.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of observations the skill writes carry a unique ID, source ID, locator,
  quoted passage, origin, confidence with a reason, derived flag, status `proposed` and
  audience `internal`, as confirmed by an automated check.
- **SC-002**: 100% of quoted passages appear word for word in the cited source at the cited
  locator, as confirmed by an automated check.
- **SC-003**: Zero observations cite a restricted source, a source's context or description
  sections, or a part of a source the consultant excluded, and zero carry origin
  `llm-inference`.
- **SC-004**: On the synthetic test set, at least 95% of observations hold exactly one claim
  with no interpretation, as judged by a reviewer, and 100% of transcript observations name
  the speaker.
- **SC-005**: On the Phase 1 trial engagement (held locally and anonymized), the observations
  proposed include the evidence behind at least 80% of the engagement's known key findings.
- **SC-006**: On the Phase 1 trial engagement, the lead consultant accepts at least 75% of
  proposed observations without edits, and can review the observations from a typical
  source in under 10 minutes.
- **SC-007**: A second run on the same source with no new focus proposes zero duplicates of
  existing or rejected observations.
- **SC-008**: Zero observations become `active`, `rejected` or `client-ready` without an
  explicit consultant instruction.

## Assumptions

- Engagement initialization (001), `charter` (002) and `ingest` (003) are in place. Sources
  are extracted markdown with stable locators, metadata and marked derived and uncertain
  passages, as `ingest` defines them.
- The observation template needs a place for the quoted passage (and, for transcripts, the
  speaker). Any such change updates every template and skill that uses it, as the
  constitution requires.
- Reviewing the inbox, accepting, editing, rejecting and moving observations into
  `30-observations/` is the job of the `triage` skill, specified separately. Until it exists,
  the consultant reviews observations by editing their front matter by hand.
- Observations are one per file, as the requirements draft prefers for traceability.
  Grouping per source is not used by this skill.
- Linking observations to findings, hypotheses or each other (`supports`, `contradicts`) is
  the work of `synthesize`, `test-hypothesis` and `find-contradictions`.
- Capturing the consultant's tacit knowledge directly is the job of `debrief` (Phase 2).
  Notes the consultant writes and ingests as a source are extracted like any other source,
  with origin `consultant-note`.
- A typical engagement has 10–20 sources; a typical source yields tens of observations,
  and long documents may need more than one session.
- One consultant runs `extract-observations` at a time per engagement.
- The skill runs inside the consultant's supported AI assistant (Claude Code initially),
  which is the only AI service it uses. Sources were already cleared for it at ingest.
- Validation uses synthetic sources in the repository, plus the Phase 1 trial engagement
  held locally and anonymized, never committed (Principle VIII).
