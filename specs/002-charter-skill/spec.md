# Feature Specification: Charter Skill

**Feature Branch**: `002-charter-skill`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Lets work on the charter skill as described in the '/Users/stanleyk/dev/cairn/requirements-draft/description.md' document."

## Clarifications

### Session 2026-11-03

- Q: Must kickoff material be ingested as a numbered source before `charter` can draw from
  it, or may `charter` read it directly? → A: Neither. `charter` never reads documents. The
  consultant summarizes the brief or statement of work in the interview, and everything
  is recorded with origin `consultant-note`.
- Q: When `charter` is re-run, can it revise existing questions, hypotheses and assumptions,
  or only add new ones? → A: Add and revise. A revised item is replaced by a new version that
  supersedes it, with a reason, logged in `changelog.md`. Items can also be rejected with a
  reason. The later `record-change` skill must follow the same rules.
- Q: When the consultant approves a hypothesis or assumption that has no evidence yet,
  should it become `active`? → A: Yes. Approval makes questions, hypotheses and
  assumptions `active`. Principle III's citation rule applies to evidence claims
  (observations and what is built on them), not to charter framing items.
- Q: If the consultant edits an item created earlier in the same session, can it be
  changed in place, or must it become a new version? → A: Items created in the current
  session that are still `proposed` may be edited in place until the session ends, with
  no new version and no changelog entry. Items from earlier sessions follow the
  supersede and clarify rules.
- Q: Once the charter is approved, what state does it take when items are later added or
  revised? → A: It stays approved, with the date and approver of the last approval. The
  summary shows how many items have been proposed since then, and approving again
  updates the date and approver.
- Q: Where are the constraints the consultant names recorded? → A: In a Constraints
  section of `scope.md`, one bullet each, tagged budget, timeline, technology, politics or
  other. Changes to it are logged as scope changes.
- Q: Can the charter be approved while some items stay `proposed`? → A: No. Approving the
  charter approves every remaining proposed item, after the consultant confirms the list.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Frame the engagement through a short interview (Priority: P1)

At kickoff, a consultant opens a newly created engagement with their AI assistant and runs
`charter`. The skill interviews them one topic at a time: objectives, boundaries,
deliverables, timeline, key questions, early hunches, assumptions, stakeholders,
constraints, and the lenses and criteria to judge options by. The consultant answers from
their own knowledge and their reading of the brief or statement of work. At the end, the
six charter files hold a draft charter: the scope written out, and each key question,
hypothesis and assumption recorded as a numbered, proposed item.

**Why this priority**: The charter is stage 1 of the pipeline. Questions and hypotheses
steer every later skill: extraction tags observations to questions, synthesis groups
evidence by question, and hypotheses tell agents what to look for and against. Without a
charter, later skills produce generic summaries.

**Independent Test**: In a freshly initialized synthetic engagement, run `charter` with
scripted answers. Confirm that `scope.md` has its objectives, boundaries, deliverables and
timeline filled in, and that `questions.md`, `hypotheses.md`, `assumptions.md`,
`stakeholders.md` and `lenses.md` hold entries in the template format, each numbered from
`-001`, marked `proposed` and with origin `consultant-note`.

**Acceptance Scenarios**:

1. **Given** a new engagement with empty charter files, **When** the consultant runs
   `charter` and answers the interview, **Then** `scope.md` contains the objectives,
   boundaries (in and out of scope), deliverables, timeline and constraints the consultant
   agreed to.
2. **Given** the consultant names three key questions, **When** the interview completes,
   **Then** `questions.md` contains `Q-001`, `Q-002` and `Q-003`, each with a title, a
   one- or two-sentence statement, a priority and who raised it.
3. **Given** the consultant shares a hunch, **When** the interview completes, **Then** it is
   recorded as a hypothesis linked to exactly one question, stating what evidence would
   confirm it and what would reject it, and that question lists the hypothesis back.
4. **Given** the consultant gives several topics in one answer (for example, objectives and
   a deadline together), **When** the interview reaches those topics, **Then** the skill
   shows what it already captured and asks the consultant to confirm it, instead of asking
   again.
5. **Given** the consultant names stakeholders, **When** the interview completes, **Then**
   each appears as a row in `stakeholders.md` with name, role, perspective and interview
   status (defaulting to "not yet interviewed").
6. **Given** the consultant stops partway through the interview, **When** the session ends,
   **Then** everything agreed so far is saved as proposed, and the summary lists the topics
   not yet covered.

---

### User Story 2 - Model-use policy settled, and no client documents read (Priority: P1)

At the start of the interview, the skill checks the engagement's model-use policy. If it is
still `unconfirmed`, the skill asks the consultant to settle it and records the answer,
along with any specific restrictions. The skill never opens or reads a client document. If
the consultant offers one, the skill declines and asks them to summarize what matters
instead.

> **Superseded** by `specs/004-charter-from-documents/spec.md`: with a settled policy that
> permits it, the skill drafts from a document in `10-sources/raw/` or pasted text.

**Why this priority**: Confidentiality is non-negotiable (Principle VIII). The engagement
record leaves the policy `unconfirmed` and says the charter is where it is confirmed.
Keeping the charter document-free means no client material reaches an external AI service
before the policy is known.

**Independent Test**: Run `charter` on synthetic engagements whose policy is `unconfirmed`,
`restricted` and `allowed`, each with a synthetic brief in `10-sources/raw/` and a scripted
request to read it. Confirm that the brief is never read in any run, and that the policy
the consultant states is recorded in both the engagement record and `scope.md`.

**Acceptance Scenarios**:

1. **Given** the policy is `unconfirmed`, **When** the consultant runs `charter`, **Then** the
   skill asks for the policy before the interview's other topics.
2. **Given** the consultant answers `allowed` or `restricted`, **When** the skill records
   it, **Then** the engagement record and the Model use section of `scope.md` both show
   the new value, along with any specific restrictions the consultant described.
3. **Given** the consultant cannot confirm the policy yet, **When** the interview continues,
   **Then** the policy stays `unconfirmed`, and the summary says it must be settled before
   any source is ingested.
4. **Given** any policy, **When** the consultant asks the skill to read the brief or another
   document, **Then** the skill declines, explains that `charter` works from the
   consultant's answers, and asks for a summary of the relevant points.

  > **Superseded** by `specs/004-charter-from-documents/spec.md` (FR-001 to FR-020): the skill uses a permitted document, and declines only when the policy or the file's location forbids it, saying what to do instead.

5. **Given** the policy is `restricted` or `unconfirmed`, **When** the interview starts,
   **Then** the skill reminds the consultant once not to paste text from client documents
   into the conversation.

---

### User Story 3 - Review and approve the charter (Priority: P2)

When the draft is complete, the skill shows the consultant a one-screen summary of the
charter: scope, questions, hypotheses, assumptions, stakeholders and lenses, with anything
missing called out. The consultant approves it all, approves some items, edits items, or
rejects items with a reason. The skill applies exactly those decisions and records when
and by whom the charter was approved.

**Why this priority**: "Approves the charter" is the consultant gate for stage 1. Only the
consultant can make an item active (Principle VII). A drafted but unapproved charter is
still useful for steering, so this ranks below drafting it.

**Independent Test**: With a drafted synthetic charter, give a scripted review that
approves two questions, rejects one hypothesis with a reason, and edits one assumption.
Confirm that only those items changed, the rejected hypothesis is still present with its
reason, the rejection is logged in `changelog.md`, and nothing else changed.

**Acceptance Scenarios**:

1. **Given** a drafted charter, **When** the consultant says "approve all", **Then** every
   proposed charter item becomes `active` and `scope.md` records the charter as approved,
   with the date and the approver.
2. **Given** a drafted charter, **When** the consultant rejects a hypothesis and gives a
   reason, **Then** the hypothesis is marked `rejected`, keeps its text, records the reason,
   and the rejection is logged in `changelog.md`. It is not deleted.
3. **Given** a drafted charter, **When** the consultant gives no instruction on an item,
   **Then** that item stays `proposed`.
4. **Given** the policy is still `unconfirmed`, **When** the consultant asks to approve the
   charter, **Then** the skill can make individual items active but does not record the
   charter as approved, and says the policy must be settled first.
5. **Given** any review, **When** the skill applies decisions, **Then** no item is marked
   `client-ready`.

---

### User Story 4 - Revise the charter as the engagement evolves (Priority: P2)

Mid-engagement, during the weekly steer, the consultant runs `charter` again. The skill
summarizes what is already there and asks what has changed. The consultant adds a new
question, sharpens an existing hypothesis, rejects an assumption that proved wrong, or
narrows the scope. Nothing is overwritten. A revised item gets a new version that
supersedes the old one, every change carries a reason and a trigger, and each change
is logged in `changelog.md` so the what-changed report can show it.

**Why this priority**: Engagements last about four weeks, and questions and hypotheses
sharpen as evidence arrives. The weekly "revise questions and hypotheses" step needs a
Phase 1 tool, and the record of how thinking changed (Principle VI) is what powers the
what-changed report.

**Independent Test**: On a synthetic engagement with an approved charter (`Q-001` to
`Q-004`, `H-001` to `H-003`), re-run `charter`. Add one question, revise `H-002`, reject
`A-001`, and change the timeline. Confirm that: the new question is `Q-005`; the revision
is a new hypothesis that supersedes `H-002`; `H-002`'s text is unchanged; `A-001` is
rejected with its reason; the old timeline is preserved in the changelog; every change
has a dated changelog entry with reason and trigger; and every other entry is unchanged.

**Acceptance Scenarios**:

1. **Given** a charter with `Q-001` to `Q-004`, **When** the consultant adds a question,
   **Then** it is recorded as `Q-005`, and `Q-001` to `Q-004` are unchanged.
2. **Given** an existing charter, **When** the skill starts, **Then** it summarizes what is
   already there and asks what the consultant wants to add or change, rather than starting
   the full interview again.
3. **Given** the consultant asks to revise `H-002` and gives a reason and a trigger,
   **When** the revision is written, **Then** a new hypothesis (for example `H-004`) is
   created with status `proposed` and a `supersedes` link to `H-002`, and `H-002` is
   unchanged until the consultant approves the new version.
4. **Given** the consultant approves the new version, **When** the skill applies it,
   **Then** the new version becomes `active`, `H-002` becomes `superseded` with the reason
   and trigger, and `changelog.md` gains a dated entry recording the supersede.
5. **Given** the consultant rejects an existing assumption with a reason, **When** the skill
   applies it, **Then** the assumption becomes `rejected`, keeps its text and the reason,
   and the rejection is logged in `changelog.md`.
6. **Given** other objects (for example observations or findings) link to an item that is
   superseded or rejected, **When** the change is applied, **Then** the summary lists every
   such object by ID so the consultant can review them.
7. **Given** the consultant changes a scope section, **When** the change is written,
   **Then** `scope.md` shows the new text, and `changelog.md` records the date, the section,
   the previous text, the reason and the trigger.

---

### User Story 5 - The skill points out gaps and suggests what's missing (Priority: P3)

After the interview, the skill checks the draft for gaps: objectives that no question
addresses, questions with no hypothesis, hypotheses that don't say what would reject them,
and deliverables with no date. It offers a short list of suggested questions, hypotheses or
assumptions. The consultant keeps or discards each one, and only kept suggestions are
written, marked as LLM inference.

**Why this priority**: Hypotheses only steer the work if they can be tested, and a missed
question at kickoff is costly later. This makes the charter better but isn't needed for a
usable one.

**Independent Test**: Draft a synthetic charter with one objective that has no question and
one question with no hypothesis. Confirm that both gaps are reported, that suggestions
are offered, and that a kept suggestion is written with origin `llm-inference` while a
discarded one is not written.

**Acceptance Scenarios**:

1. **Given** an objective that no question addresses, **When** the gap check runs, **Then**
   the skill names the objective and offers a question that would cover it.
2. **Given** the consultant keeps a suggested hypothesis, **When** it is written, **Then** its
   origin is `llm-inference`, its status is `proposed`, and its confidence reason says it was
   suggested by the skill.
3. **Given** the consultant discards a suggestion, **When** the session ends, **Then** it
   appears in no charter file.

---

### Edge Cases

- The skill is run outside an engagement folder (no engagement record can be found): it
  stops and explains how to create an engagement first.
- Charter files already contain hand-written entries: they are kept as they are, their
  IDs count as taken, and new entries are numbered after the highest existing one.
- Charter files contain duplicate or malformed IDs (for example, two `Q-003` entries from a
  hand edit): the skill reports them and does not renumber or fix them itself.
- The consultant states a hunch that fits no existing question: the skill offers a
  question for it, or asks the consultant which question it answers. It never writes a
  hypothesis with no question.
- The consultant gives a "question" that is really a hunch, or the other way round: the
  skill suggests the other type, and the consultant decides.
- The consultant names many key questions (more than about ten): the skill records them all
  and suggests marking priorities so the work stays focused.
- A question is superseded and active hypotheses link to it: the skill lists them and asks
  which should move to the new version. A hypothesis that moves keeps its claim; only its
  question link changes, and the change is logged.
- The consultant asks to revise an item without giving a reason: the skill asks for one
  before writing the revision. It also asks what triggered it: new evidence, client
  feedback or rethinking.
- The consultant asks to revise an item that is already superseded or rejected: the skill
  points to the current version, or says the item was dropped, and asks how to proceed.
- The consultant asks to edit an item's wording without changing its meaning: the skill
  records it as a clarification of that item, logged in `changelog.md`, rather than a new
  version.
- The engagement uses a client code name: the skill refers to the client by the code name
  in every charter file, and does not write the real client name into any of them.
- The consultant mentions sensitive personal detail about a stakeholder (for example,
  credibility or politics): it is recorded in the stakeholder's perspective only if the
  consultant confirms it should be, and the item stays `internal`.

## Requirements *(mandatory)*

### Functional Requirements

**Starting**

- **FR-001**: The `charter` skill MUST be bundled with the framework, so new engagements
  include it and existing engagements gain it on refresh.
- **FR-002**: The skill MUST find the engagement record before doing anything else, and MUST
  stop with an explanation if it isn't run inside an engagement.
- **FR-003**: The skill MUST read the existing charter files first, so that it doesn't ask
  for what is already recorded and numbers new items after existing ones. If a charter
  already exists, the skill MUST start in revision mode (User Story 4) instead of running
  the full interview.

**Model-use policy and documents**

- **FR-004**: At the start of each session, the skill MUST check the model-use policy in the
  engagement record. If it is `unconfirmed`, the skill MUST ask the consultant to settle it
  before covering any other topic. The consultant MAY decline to settle it yet.
- **FR-005**: When the consultant settles the policy, the skill MUST record the value in the
  engagement record (the authoritative copy) and in the Model use section of `scope.md`,
  together with any specific restrictions the consultant describes.
- **FR-006**: The skill MUST NOT open or read any client document, in `10-sources/` or
  anywhere else. If asked to, it MUST decline and ask the consultant to summarize the
  relevant points.

  > **Superseded** by `specs/004-charter-from-documents/spec.md` (FR-001 to FR-020): `charter` may draft from a document in `10-sources/raw/` or pasted text, once the model-use policy permits it. The text above is kept for history.

- **FR-007**: When the policy is `restricted` or `unconfirmed`, the skill MUST remind the
  consultant once, at the start, not to paste client document text into the conversation.

**Interview**

- **FR-008**: The interview MUST cover: objectives; boundaries (in and out of scope);
  deliverables; timeline; key questions; hunches; assumptions; stakeholders; constraints
  (such as budget, timeline, technology and politics); and lenses and evaluation criteria.
- **FR-009**: Objectives and at least one key question are the minimum for a draft charter.
  Every other topic MAY be skipped; skipped topics MUST be listed in the end summary.
- **FR-010**: The skill MUST cover one topic at a time. When an earlier answer already
  covers a topic, the skill MUST present what it captured for confirmation rather than ask
  the consultant to restate it.
- **FR-011**: The consultant MUST be able to give input during the interview or up front
  when invoking the skill. The skill MUST skip questions already answered.
- **FR-012**: The skill MUST offer a starting set of common lenses (cost, risk, customer
  experience, operating model), which the consultant can accept, change or replace.

**Writing the charter**

- **FR-013**: The skill MUST write objectives, boundaries, deliverables, timeline and
  constraints under the matching headings in `scope.md`, keeping its front matter and
  Model use section. Constraints go in a Constraints section, one bullet each, tagged
  budget, timeline, technology, politics or other. If an older `scope.md` has no
  Constraints heading, the skill adds one.
- **FR-014**: The skill MUST record each key question as a `Q-###` entry in
  `questions.md`, each hypothesis as an `H-###` entry in `hypotheses.md`, and each
  assumption as an `A-###` entry in `assumptions.md`, using the engagement's templates.
- **FR-015**: Each hypothesis MUST link to exactly one question and MUST state what evidence
  would confirm it and what would reject it. The question MUST list the hypothesis back,
  so the link is consistent in both directions.
- **FR-016**: Each assumption MUST record its basis and the questions it affects.
- **FR-017**: Each stakeholder MUST be recorded as a row in `stakeholders.md` with name,
  role, perspective and interview status. Lenses and evaluation criteria MUST be recorded
  under the matching headings in `lenses.md`.
- **FR-018**: Every new question, hypothesis and assumption MUST have status `proposed`,
  audience `internal`, and a confidence with a one-line reason. Its origin MUST be
  `consultant-note` for anything from the consultant's answers (including their summary
  of kickoff material) and `llm-inference` for the skill's own suggestions.
- **FR-019**: Because nothing the skill writes is drawn from a source document, the skill
  MUST NOT cite a source ID or attribute any item to `client-document` origin. Once
  sources are ingested, linking charter items to supporting evidence is left to later
  skills.

  > **Superseded in part** by `specs/004-charter-from-documents/spec.md` (FR-001 to FR-020): the premise "nothing the skill writes is drawn from a source document" no longer holds. Document-drawn items still never cite a source ID or use `client-document`; they stay `consultant-note` with the document named in `confidence_reason`.

- **FR-020**: New IDs MUST be the next free number for their type, MUST NOT reuse any
  existing number, and links between items MUST use IDs only.
- **FR-021**: The skill MUST NOT delete any charter entry, MUST NOT change an existing
  item's claim in place, and MUST NOT modify anything in `10-sources/raw/`. An item is
  *existing* if it was in the charter files when the session started. Items created in
  the current session that are still `proposed` MAY be edited in place until the session
  ends, without a new version or a changelog entry.
- **FR-022**: The skill MUST save agreed items as it goes, so that stopping partway loses
  nothing already agreed.

**Revising the charter**

- **FR-023**: The skill MUST revise an existing question, hypothesis or assumption only on
  the consultant's explicit request, and MUST get a reason and a trigger (new evidence,
  client feedback or rethinking) before writing anything.
- **FR-024**: A revision that changes an item's claim MUST be written as a new item with the
  next free ID, status `proposed` and a `supersedes` link to the old item. The old item MUST
  stay unchanged until the consultant approves the new version. On approval, the new
  version MUST become `active` and the old item MUST become `superseded`, keeping its text,
  with the reason and trigger recorded.
- **FR-025**: A wording change that keeps an item's claim MUST be recorded as a
  clarification of that item, not a new version.
- **FR-026**: The consultant MUST be able to reject an existing item with a reason. The item
  MUST become `rejected` and keep its text and the reason.
- **FR-027**: Changes to a scope section MUST replace the text in `scope.md`, and
  `changelog.md` MUST record the previous text.
- **FR-028**: Every supersede, clarification, rejection, scope change and moved hypothesis
  link MUST be logged in `changelog.md` with the date, the item ID or scope section, what
  changed, the reason and the trigger.
- **FR-029**: When an item is superseded or rejected, the skill MUST list every object in
  the engagement that links to it, by ID, so the consultant can review them. For active
  hypotheses linked to a superseded question, the skill MUST ask which should move to the
  new version.
- **FR-030**: The supersede, clarify and reject rules in FR-023 to FR-029 MUST be written
  down as one shared convention, which the later `record-change` skill will also follow.

**Gap check and suggestions**

- **FR-031**: After the interview or a revision, the skill MUST report gaps: objectives that
  no active or proposed question addresses, questions with no hypothesis, hypotheses with
  no rejection condition, and deliverables with no date.
- **FR-032**: The skill MAY suggest up to five additional questions, hypotheses or
  assumptions per session. Each suggestion MUST be shown to the consultant first, and only
  those the consultant keeps MAY be written, with origin `llm-inference`.

**Review and approval**

- **FR-033**: The skill MUST present a one-screen summary of the charter for review: scope,
  each item by ID, title and status, pending revisions, gaps, and model-use status.
- **FR-034**: The skill MUST change an item's status only on the consultant's explicit
  instruction in the session: approve (to `active`), reject (to `rejected`, with a reason)
  or approve a revision (FR-024). Items with no instruction MUST stay `proposed`.
- **FR-035**: When the consultant approves the charter as a whole, the skill MUST record the
  approval date and approver in `scope.md`. Approving the charter as a whole approves every
  item that is still `proposed`, including pending new versions (FR-024). The skill first
  lists those items and asks the consultant to confirm. An item the consultant wants to hold
  back must be rejected, or approval of the charter put off. It MUST NOT record approval while the
  model-use policy is `unconfirmed`. Later additions and revisions MUST NOT reset an
  approved charter to draft. The review summary MUST show how many items have been
  proposed since the last approval, and approving again MUST update the date and
  approver.
- **FR-036**: The skill MUST NOT set any item to `client-ready`, and MUST NOT mark an
  `llm-inference` item as confirmed against a source.

**Confidentiality and wrap-up**

- **FR-037**: When the engagement uses a client code name, the skill MUST use the code name
  in every charter file and log entry, and MUST NOT write the real client name into any of
  them.
- **FR-038**: The skill MUST NOT send engagement information to any service other than the
  consultant's AI assistant, and MUST NOT perform web or prior-work research. Research
  belongs to `research-question` and `find-prior-art`.
- **FR-039**: At the end of each session, the skill MUST show a summary listing the items
  written or changed (by ID), topics not yet covered, objects flagged for review, the
  model-use status, and next steps (review and approve the charter, add originals to
  `10-sources/raw/`, ingest sources).

### Key Entities

- **Charter**: The engagement's framing, held in the six files of `00-charter/`. It has a
  draft or approved state, with the approval date and approver recorded in `scope.md`.
- **Scope**: Objectives, boundaries, deliverables, timeline, constraints and the model-use
  policy, held in `scope.md`. Not a numbered object; its changes are logged in `changelog.md`.
- **Question (`Q-###`)**: Something the engagement must answer. Has a priority, who raised
  it, and the hypotheses that answer it.
- **Hypothesis (`H-###`)**: A working answer to one question, with what would confirm or
  reject it. Usually starts as the consultant's hunch.
- **Assumption (`A-###`)**: Something taken as true without direct evidence, with its basis
  and the questions it affects.
- **Stakeholder**: A person involved in the engagement, with role, perspective and
  interview status. A table row, not a numbered object.
- **Lens / evaluation criterion**: A reusable way to analyze the problem, or a criterion
  options will be judged against. Named in later requests instead of retyped.
- **Model-use policy**: `allowed`, `restricted` or `unconfirmed`, with any specific
  restrictions. Authoritative in the engagement record; copied into `scope.md`.
- **Change event**: A dated entry in `changelog.md` recording a supersede, clarification,
  rejection, scope change or moved link: which item or section, what changed, the reason
  and the trigger.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a typical engagement, a consultant goes from running `charter` to a
  reviewed draft charter in under 30 minutes.
- **SC-002**: A revision session that adds or changes up to five items takes under 10
  minutes.
- **SC-003**: 100% of questions, hypotheses and assumptions the skill writes carry a unique
  ID, status, origin, confidence with a reason, and audience `internal`, as confirmed by an
  automated check of the charter files.
- **SC-004**: 100% of hypotheses link to exactly one existing question, and every such
  link appears on both the hypothesis and the question.
- **SC-005**: In test runs, the skill reads zero client documents, whatever the
  model-use policy.

  > **Superseded** by `specs/004-charter-from-documents/spec.md` (FR-001 to FR-020): under 004 the skill reads zero documents under `unconfirmed` and only cleared documents otherwise (004 SC-003).

- **SC-006**: Across revision test runs, zero existing items have their claim changed in
  place, zero items are deleted, and 100% of supersedes, clarifications, rejections and
  scope changes have a dated changelog entry with reason and trigger.
- **SC-007**: Zero items become `active`, `rejected` or `superseded` without an explicit
  consultant instruction, and zero become `client-ready`.
- **SC-008**: On the Phase 1 trial engagement (held locally and anonymized), the lead
  consultant judges that the charter captures at least 80% of the key questions the
  engagement actually set out to answer.
- **SC-009**: In review of test sessions, the skill never asks the consultant to restate
  something they already gave earlier in the session or that is already in the charter.

## Assumptions

- Engagement initialization (feature 001) is in place. The engagement record, the six
  charter seed files and the question, hypothesis and assumption templates exist in the
  formats it defines, and the skill writes to them as they are.
- The skill runs inside the consultant's supported AI assistant (Claude Code initially). The
  interview is a conversation in that assistant, in English.
- One consultant runs `charter` at a time per engagement. Simultaneous edits by several
  analysts are out of scope.
- The consultant reads the brief or statement of work themselves and summarizes it in the
  interview. What they type into the conversation is their responsibility. The skill only
  reminds them of the policy.
- Applying the consultant's approve, reject and revise decisions is allowed under
  Principle VII, because the decision is the consultant's and the skill only records it,
  as `triage` will.
- Questions, hypotheses and assumptions are framing items, not evidence claims. An
  `active` hypothesis is the one being tested, not one shown to be true. So Principle
  III's rule that an uncited claim cannot become active does not apply to them, and
  approval makes them `active` without a citation.
- Approving an item makes it `active` but leaves it `internal`. Making anything
  `client-ready` is a separate, later consultant decision.
- Charter approval is recorded in `scope.md`, not as a `D-###` decision. Decisions in
  `60-log/decisions.md` are for choosing or rejecting options.
- Flagging linked objects for review means listing them in the session summary. A
  persistent review flag on those objects is left to `record-change` (Phase 2), which
  will adopt the convention from FR-030.
- In Phase 1, few objects will link to charter items yet, since extraction and synthesis
  run after the charter. Listing linked objects (FR-029) matters most from the second week.
- Stakeholder names and perspectives are client data that stays in the engagement folder
  (Principle VIII). Nothing from the charter leaves the engagement.
- Validation uses a synthetic engagement in the repository, plus the Phase 1 trial
  engagement held locally and anonymized, never committed (Principle VIII).
- Web research, prior-art search, debriefs after meetings and ingesting sources are other
  skills' jobs and are out of scope here.
