# Feature Specification: Charter-Relevant Observations

**Feature Branch**: `006-charter-relevant-observations`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "In testing the implementation of the skill extract-observations, I noticed that it created an enormous number of observations, each in their own file (see '_inbox') derived from the extracted content of a transcript '10-sources/extracted/S-001.md'. I think this is because the definition of a relevant observation was not required, nor defined. Instead I would like to modify the skill to focus on finding observations that are relevant to the charter. Observations that do not relate to the charter should not be captured as formal observations."

## Context

This feature changes the `extract-observations` skill (feature 005). It reverses one
decision recorded there: spec 005's clarification and research decision R1 said that with no
focus, the skill extracts **every factual claim** and keeps untagged claims.

In a trial on a real engagement, one meeting transcript of about 1,200 lines produced 157
proposed observations in `_inbox/`. Only 15 were untagged. The rest carried question tags,
but many had a weak link to the question at best. Examples (anonymised):

- a remark that the client doesn't use a particular chat tool;
- a stakeholder's previous employer;
- five separate observations describing a tool the speaker used at another company in 1999,
  four of them tagged to the build-versus-buy question.

So simply dropping untagged claims would not be enough. The skill needs a stated test of
what makes a claim relevant to the charter, and it must apply that test to every claim before
proposing it.

## Clarifications

### Session 2026-11-09

- Decision (from the feature request): claims that don't relate to the charter are not
  captured as observations. There is no "every claim" mode. This replaces 005's R1.
- Q: When the consultant re-runs the skill with no focus on a source already fully processed,
  should it check the source again against all current charter questions? → A: Yes. A plain
  re-run checks against every current question and proposes only claims no existing
  observation holds. It does not ask for confirmation.
- Q: Should the skill limit or flag how many observations one source produces? → A: No hard
  limit; the relevance test decides. When a source's count is unusually high, the summary
  flags it and suggests a narrower focus.
- Q: How complete should the "Passed over" list in the summary be? → A: Every distinct
  off-charter topic longer than a passing remark (about 3 or more turns, or a paragraph or
  more), each with a label and locator range. Brief asides are grouped into one "other brief
  remarks" line with a count.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Only charter-relevant claims become observations (Priority: P1)

The consultant ingests a 90-minute kickoff meeting transcript as `S-001` and runs
`extract-observations S-001`. The transcript covers the charter's questions, but also
introductions, small talk, anecdotes about past jobs, and remarks about office tools. The
skill reads the charter: its questions, the hypotheses and assumptions linked to them, and
the scope. It proposes an observation only for a claim that is evidence for answering a
charter question, or for testing a hypothesis or assumption. Every observation it writes is
tagged to at least one question and gives a one-line reason saying how it bears on that
question. The introductions, anecdotes and tool remarks produce no observations.

**Why this priority**: This is the problem the consultant hit. Without a relevance test, a
single meeting buries the consultant in review work. Most of the items have no value
downstream, and the useful evidence gets lost among them.

**Independent Test**: In a synthetic engagement with an approved charter (three questions,
two hypotheses), ingest a synthetic transcript seeded with known relevant claims and known
off-charter material (introductions, anecdotes, tool remarks, scheduling). Run
`extract-observations` on it. Check that every proposed observation has at least one
question tag and a relevance reason. Check that none of the seeded off-charter claims
became an observation, and that the seeded relevant claims did.

**Acceptance Scenarios**:

1. **Given** a source and a charter with questions, **When** the skill extracts with no
   focus, **Then** it proposes only claims that bear on at least one charter question, and
   writes no untagged observations.
2. **Given** a claim that bears on no charter question (small talk, introductions, past
   jobs, anecdotes, logistics, tool preferences with no link to the scope), **When** the
   skill meets it, **Then** it does not write it as an observation.
3. **Given** a claim the skill does propose, **When** it is written, **Then** it carries at
   least one question tag and a one-line reason naming what the claim tells the consultant
   about that question.
4. **Given** a claim that bears on a hypothesis's confirm or reject condition, or on an
   assumption, **When** the skill extracts, **Then** it treats the claim as relevant and tags
   it with the question that the hypothesis or assumption belongs to.
5. **Given** a long passage on one charter topic, **When** the skill extracts, **Then** it
   proposes the distinct claims that matter for the question. It does not split every
   sentence into its own observation, and it does not repeat a point the speaker makes
   several times.
6. **Given** a claim on a topic the scope explicitly excludes (for example org design or
   hiring, when out of scope), **When** the skill meets it, **Then** it does not propose it,
   unless the claim also bears on an in-scope question.

---

### User Story 2 - See what was passed over (Priority: P2)

After the run, the consultant wants to be sure nothing important was dropped. The summary
reports each off-charter topic the skill passed over: "Passed over as off-charter:
introductions (T1–T12), a past project at another company (T140–T171), office tools
(T88–T93); other brief remarks: 6". The consultant can see at a glance
what was left out and why. If something there matters after all, they can add a question
with `/charter` and re-run, or write an observation themselves.

**Why this priority**: The consultant decides what matters (constitution VII). A filter that
drops material silently would take that decision away. A short account of what was passed
over keeps the consultant in control, without adding any files.

**Independent Test**: Run the skill on the synthetic transcript from US1. Check that the
summary has a "Passed over" section that names each seeded off-charter topic of 3 or more
turns with its locator range, and counts the seeded brief asides on one "other brief
remarks" line. Check that no files were written for them.

**Acceptance Scenarios**:

1. **Given** a run that passed over material, **When** the skill reports, **Then** the
   summary lists every distinct passed-over topic longer than a passing remark (about 3 or
   more turns, or a paragraph or more), each with a short label and a locator or locator
   range, and groups shorter asides into one "other brief remarks" line with a count.
2. **Given** a passed-over topic, **When** it is listed, **Then** the skill writes no file,
   log entry or other record for it beyond the summary.
3. **Given** passed-over material that looks important but fits no current question (for
   example a new risk the charter doesn't cover), **When** the skill reports, **Then** it
   says so in one line and suggests `/charter` to add a question. It doesn't create the
   question itself.
4. **Given** a source that yields more observations than the density threshold (FR-016),
   **When** the skill reports, **Then** the summary flags that source's count and suggests
   re-running with a narrower focus. Nothing is dropped because of the count.

---

### User Story 3 - Charter changes bring in new evidence (Priority: P2)

Two weeks later, the consultant adds Q-005 to the charter. Material in `S-001` that was
passed over before now bears on Q-005. The consultant runs
`extract-observations S-001 for Q-005`. The skill proposes the claims that bear on Q-005,
even though `S-001` was already marked as fully processed. It doesn't re-propose claims that
existing observations already hold.

**Why this priority**: Questions change over time. That was the reason 005 kept every claim.
Re-running against the new question gets the same recall without a flood of observations up
front.

**Independent Test**: In the US1 engagement, add a question that matches one seeded
off-charter topic. Re-run with a focus on the new question. Check that the skill proposes
the claims for that topic, and that it proposes no claim already held by an existing
observation.

**Acceptance Scenarios**:

1. **Given** a source already processed in full, **When** the consultant re-runs it with a
   focus on a question added since, **Then** the skill extracts from it without asking for
   override confirmation, and proposes claims that bear on the new question.
2. **Given** a re-run, **When** a claim is already held by an existing observation, **Then**
   the skill doesn't propose it again, but may offer to tag the existing observation with
   the new question (as in 005, FR-023).
3. **Given** a source already processed in full and a question added since, **When** the
   consultant re-runs it with no focus, **Then** the skill checks it against every current
   question without asking for confirmation, and proposes only claims that no existing
   observation holds.

---

### User Story 4 - No charter, no extraction (Priority: P3)

A consultant runs `extract-observations` before the charter has any questions. The skill
explains that observations are judged against the charter's questions, and that there are
none yet. It suggests `/charter`, and stops without reading the source.

**Why this priority**: Without questions there is nothing to test relevance against. In
005 this case led to every claim going in untagged, which is exactly the flood this feature
removes.

**Independent Test**: In a synthetic engagement with no questions, run the skill on an
ingested source. Check that it reads no source, writes nothing, and points to `/charter`.

**Acceptance Scenarios**:

1. **Given** a charter with no usable questions (none, or only rejected or superseded ones),
   **When** the consultant runs the skill, **Then** it writes nothing, reads no source, and
   suggests `/charter`.
2. **Given** a charter whose questions are still `proposed` (charter in draft), **When** the
   consultant runs the skill, **Then** it extracts against those questions, and the summary
   notes that the charter is not yet approved.

---

### Edge Cases

- **A claim relevant only through context** (for example, "we only have one person doing
  this", said while discussing a broken process): it is relevant if the passage itself ties
  it to the charter topic. The claim must still be stated without interpretation. The
  relevance reason explains the link; the claim does not.
- **Stakeholder background** (a person's role, history or reporting line): not an
  observation, unless it bears on a question, for example who owns an executive figure. The
  summary may suggest updating stakeholders with `/charter`.
- **Wishes and feature ideas** ("it would be great if a tool could brief me on any
  account"): relevant only when a question covers the capabilities the client needs. Then
  the claim is stated as the speaker's wish, never as a requirement.
- **Focus steering**: a focus still narrows the run to the named questions. Relevance to the
  charter is the baseline, and the focus narrows it further.
- **Perspective steering**: changes which relevant claims are favoured, never whether an
  off-charter claim is kept.
- **Borderline claims**: when the skill can't tell whether a claim bears on a question, it
  leaves it out and mentions the topic under "Passed over", rather than proposing it with a
  weak tag.
- **Existing untagged or weakly tagged observations** from earlier runs are left as they
  are. The consultant handles them in triage. This feature does not change or reject
  existing observations.
- **A source with almost nothing relevant** (for example, a social call): the skill proposes
  nothing, or very little, and the summary says so plainly. This is a normal result, not an
  error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The skill MUST apply a relevance test to every candidate claim before proposing
  it. A claim is relevant when it is evidence that could help answer an active or proposed
  charter question, or help confirm or reject a hypothesis or assumption linked to one.
- **FR-002**: The skill MUST NOT write an observation for a claim that fails the relevance
  test. There is no "every claim" mode. (This replaces 005 R1 and the "untagged" part of
  005 FR-017.)
- **FR-003**: Every observation the skill writes MUST carry at least one question tag. The
  skill MUST NOT write untagged observations.
- **FR-004**: Every observation the skill writes MUST record a one-line relevance reason
  saying how the claim bears on its tagged question or questions. The reason is the skill's
  judgment and is kept apart from the claim, which stays free of interpretation (005 FR-010).
- **FR-005**: The skill MUST tag a question only when the claim bears on that question
  directly. It MUST NOT add a tag just because the topic is loosely related.
- **FR-006**: The skill MUST use the charter's questions, the hypotheses and assumptions
  linked to them (including confirm and reject conditions), and the scope's in-scope and
  out-of-scope lists, to judge relevance. It MUST NOT treat a claim that touches only an
  out-of-scope topic as relevant.
- **FR-007**: When a claim's relevance is unclear, the skill MUST leave it out and report its
  topic under "Passed over". It MUST NOT propose the claim with a weak tag.
- **FR-008**: The skill MUST prefer the distinct claims that matter for a question over an
  exhaustive split of every sentence. It splits a passage into several observations only
  when each part is relevant on its own (refines 005's "one claim per observation"
  guidance, without changing the one-claim rule).
- **FR-009**: The session summary MUST include a "Passed over" section. It lists every
  distinct off-charter topic longer than a passing remark (about 3 or more turns, or a
  paragraph or more), each with a short label and a locator or locator range; shorter
  asides are grouped into one "other brief remarks" line with a count. It also notes
  briefly any passed-over material that looks important but fits no current question,
  suggesting `/charter`. The summary MUST NOT include an "Untagged" section.
- **FR-010**: The skill MUST NOT write any file, log entry or record for passed-over material
  beyond the summary.
- **FR-011**: When the charter has no active or proposed questions, the skill MUST stop
  before reading any source, write nothing, and suggest `/charter`.
- **FR-012**: When the charter is not yet approved, the skill MUST extract against its
  proposed questions and say in the summary that the charter is unapproved.
- **FR-013**: A source recorded as fully processed MUST still be extractable, without
  override confirmation. With a focus, the skill extracts against the focus questions. With
  no focus, it checks the source again against every current charter question. Existing
  duplicate and rejected-claim checks still apply (005 FR-022), so only claims that no
  existing observation holds are proposed. Existing observations may still be offered for
  retagging (005 FR-023).
- **FR-014**: The skill's guidance for consultants and its worked examples MUST define
  relevance, with examples of relevant and off-charter claims. The examples MUST be
  synthetic (constitution VIII).
- **FR-015**: All other behaviour of 005 is unchanged: citation, exact passages, locators,
  speaker attribution, confidence caps, derived flags, steering, natural breaks, and the
  "Never" rules.
- **FR-016**: The skill MUST NOT impose a hard limit on observations per source; the
  relevance test alone decides what is proposed. When one run proposes more than one
  observation per 10 transcript turns, or more than one per page for paged documents, the
  summary MUST flag that source's count and suggest a narrower focus. The existing
  per-session natural break (005) still applies.

### Key Entities

- **Observation** (changed): gains a one-line **relevance reason** linking the claim to its
  tagged questions. Its question tags may no longer be empty.
- **Relevance test** (new concept): the rule in FR-001 and FR-006 that decides whether a
  candidate claim becomes an observation. It is judged against the charter's questions,
  hypotheses, assumptions and scope.
- **Passed-over topic** (summary only, not stored): a label and a locator range for
  material the skill left out as off-charter. Brief asides are only counted, not labelled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a synthetic meeting transcript with an answer key, 100% of proposed
  observations carry at least one question tag and a relevance reason.
- **SC-002**: On the same transcript, none of the seeded off-charter claims becomes an
  observation, and at least 90% of the seeded charter-relevant claims do.
- **SC-003**: When the consultant re-runs the trial transcript (the one that produced 157
  observations), the skill proposes at least 60% fewer observations, and the consultant
  judges no important charter evidence to be missing.
- **SC-004**: When the consultant reviews a sample of 20 proposed observations, they agree
  with the relevance reason for at least 18.
- **SC-005**: The consultant can triage the observations from a 90-minute meeting in under
  20 minutes.
- **SC-006**: After a question is added, re-running a source with a focus on it recovers at
  least 90% of the seeded claims for that question that were passed over before.

## Assumptions

- "Relevant to the charter" is judged against questions, because hypotheses and assumptions
  each link to a question and the scope's objectives are expressed through the questions.
  Tags remain question IDs only. The skill still sets no links to hypotheses (005 FR-018).
- Material that is useful but not evidence (stakeholder background, scheduling, contacts)
  belongs in the charter or the consultant's notes, not in observations.
- The consultant prefers a short, high-signal inbox. If a borderline claim is missed, the
  consultant can recover it by re-running with a focus or adding a question. Losing that
  claim costs less than reviewing many marginal ones.
- No change to the observation's ID scheme, file-per-observation layout or triage flow.
- No migration: observations created under 005's every-claim rule stay as they are.
- The trial engagement that exposed the problem holds real client data. It is used only for
  the consultant's own check (SC-003) and never copied into the repository. All tests and
  fixtures are synthetic.
