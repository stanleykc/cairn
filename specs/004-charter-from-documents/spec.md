# Feature Specification: Charter From Engagement Documents

**Feature Branch**: `004-charter-from-documents`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "When I try to run the \"/charter\" skill it asks me to answer 10 questions. Many of these questions could potentially be answered by a document related to the engagement - e.g., the statement of work (SOW). When I try and use that document, or even copy/pasted content from that document, it is rejected with a message like \"I can't use this either. It's the same SOW text again, and I don't record scope from documents.\". Modify this skill to allow me to use a document to answer one or more of these questions."

## Clarifications

### Session 2026-11-05

- Q: How can a document be supplied? → A: Only a file in `10-sources/raw/`, or pasted
  text. Files elsewhere are not read; the consultant copies them into `10-sources/raw/`
  first.
- Q: How are items taken from a document labeled? → A: Origin `consultant-note`, with the
  document named in the confidence reason. No source ID, no `client-document` origin, no
  constitution amendment.

## Background

Today `charter` never reads a document (002 spec, FR-006 and FR-019). It declines file
paths and also refuses pasted document text, so the consultant must retype in their own
words what the statement of work (SOW), brief or proposal already says. The rule existed
to keep client material away from external AI services before the model-use policy was
known (Principle VIII). This feature keeps that protection, since the policy is still
settled first, but lets the consultant use a document as input to the interview once it
is safe to do so.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pre-fill the interview from a document (Priority: P1)

At kickoff the consultant has the signed SOW. They run `charter` and point it at the
document. Once the model-use policy allows it, the skill reads the document and drafts
answers for every interview topic it covers: objectives, boundaries, deliverables,
timeline, constraints, stakeholders and any stated questions. It then walks the
consultant through the topics one at a time, as today, showing each drafted answer for
confirmation or correction instead of asking a blank question. Topics the document does
not cover are asked as usual. Nothing is written until the consultant confirms the topic.

**Why this priority**: This is the request. It removes the retyping of material that
already exists and is the slowest part of a first charter session.

**Independent Test**: In a synthetic engagement with `model_use: allowed`, give `charter`
a synthetic SOW that covers objectives, scope, deliverables and timeline but not
hypotheses or lenses. Confirm that those four topics are shown pre-filled for
confirmation, the remaining topics are asked normally, and the files hold only what the
consultant confirmed.

**Acceptance Scenarios**:

1. **Given** the policy is `allowed` and the consultant names a document, **When** the
   interview starts, **Then** the skill reads it and lists which topics it found answers
   for and which it did not.
2. **Given** a topic the document covers, **When** the skill reaches it, **Then** it shows
   the drafted answer, using the document's own wording where practical, and asks the
   consultant to confirm, correct or skip it.
3. **Given** the consultant corrects a drafted answer, **When** the topic is saved, **Then**
   the corrected version is written, not the document's version.
4. **Given** a topic the document does not cover, **When** the skill reaches it, **Then** it
   asks the usual interview prompt.
5. **Given** the consultant pasted document text into the conversation instead of naming a
   file, **When** the policy permits it, **Then** the skill treats the pasted text the same
   way as a named document instead of rejecting it.

---

### User Story 2 - Model-use policy still gates every document (Priority: P1)

Before reading any document or using pasted document text, the skill makes sure the
model-use policy is settled and permits it. If the policy is `unconfirmed`, the skill asks
for it first, as today; if it stays unconfirmed, the skill does not read the document and
carries on with the plain interview. If the policy is `restricted`, the skill shows the
recorded restrictions and asks the consultant to confirm that this document may be used
before reading it.

**Why this priority**: Confidentiality is non-negotiable (Principle VIII). Allowing
documents is only acceptable if the policy check happens first, every time.

**Independent Test**: Run the same synthetic SOW request against engagements whose policy
is `unconfirmed`, `restricted` and `allowed`. Confirm the document is read only in the
`allowed` run and in the `restricted` run after the consultant confirms, and never in the
`unconfirmed` run.

**Acceptance Scenarios**:

1. **Given** the policy is `unconfirmed` and the consultant names a document, **When** they
   cannot settle the policy, **Then** the skill does not open the document, explains why,
   and offers the plain interview.
2. **Given** the policy is `unconfirmed`, **When** the consultant settles it to `allowed` in
   the session, **Then** the skill may then read the document.
3. **Given** the policy is `restricted`, **When** the consultant names a document, **Then**
   the skill shows the recorded restrictions and reads the document only after the
   consultant confirms it is permitted.
4. **Given** the policy is `restricted` and the consultant says the document is not
   permitted, **When** the interview continues, **Then** the skill does not read it and
   asks for a summary instead, as today.
5. **Given** the policy is `restricted` or `unconfirmed`, **When** the interview starts,
   **Then** the existing one-time reminder not to paste document text still appears, now
   saying pasted text is used only once the policy permits it.

---

### User Story 3 - Visible provenance for document-drawn items (Priority: P2)

Every question, hypothesis, assumption and scope entry that came from a document is
recorded so the consultant and later skills can tell it came from that document and not
from the consultant's own judgment.

**Why this priority**: Principle IV requires that a reader can tell what a source said
from what a person or model concluded. Without it, document content would look like
consultant opinion.

**Independent Test**: After a session that used a SOW, inspect every item written. Each
item drawn from the document carries the provenance defined in FR-012; items from the
consultant's own answers keep `consultant-note`; kept suggestions keep `llm-inference`.

**Acceptance Scenarios**:

1. **Given** a confirmed item drawn from the document, **When** it is written, **Then** it
   carries the document provenance defined in FR-012.
2. **Given** the consultant substantially rewrote a drafted item, **When** it is written,
   **Then** it is recorded as `consultant-note`.
3. **Given** the session used a document, **When** the end summary is shown, **Then** it
   names the document and lists which topics were drawn from it.

---

### User Story 4 - Use a document in revision mode (Priority: P3)

Mid-engagement the client issues a change order or an amended SOW. The consultant runs
`charter` on an existing charter and points it at the new document. The skill compares
the document to the current charter and proposes the changes it implies (new items,
revisions, rejections), each shown for confirmation and each following the existing
supersede and clarify rules with a reason and a trigger.

**Why this priority**: Useful, but less frequent than kickoff, and it builds on the
existing revision rules.

**Independent Test**: In a synthetic engagement with an approved charter, give `charter` a
synthetic change order that moves the final readout date and adds one deliverable.
Confirm the skill proposes exactly those two changes and records nothing until confirmed.

**Acceptance Scenarios**:

1. **Given** an existing charter and a new document, **When** the skill reads it, **Then** it
   lists only the differences between the document and the charter.
2. **Given** a proposed revision, **When** the consultant confirms it, **Then** it follows the
   change convention, with the document named as the trigger.

### Edge Cases

- The document conflicts with what the consultant says in the session: the consultant's
  answer wins, and the skill points out the conflict once.
- The document names the real client while a code name is in use: the skill writes only
  the client label (existing FR-037).
- The document cannot be read (unsupported format, password-protected, scanned with no
  text): the skill says so and continues with the plain interview.
- The consultant names several documents: each is checked against the policy and read in
  turn; conflicts between them are shown to the consultant to resolve.
- The document is very long: the skill uses only what bears on the interview topics and
  does not reproduce the document.
- The document is in `10-sources/raw/`: the skill reads it without modifying, moving or
  renaming it (Principle II).
- The document contains hunches or hypotheses written as facts: the skill presents them as
  candidate hypotheses or assumptions, never as confirmed facts.

## Requirements *(mandatory)*

### Functional Requirements

**Accepting a document**

- **FR-001**: The consultant MUST be able to offer a document as input to `charter`, up
  front with the command or at any point in the interview, in one of two ways: by naming a
  file in `10-sources/raw/`, or by pasting its text into the conversation. If the
  consultant names a file outside `10-sources/raw/`, the skill MUST NOT read it, and MUST
  ask them to copy it into `10-sources/raw/` first (or paste the relevant text).
- **FR-002**: Pasted document text MUST be treated the same way as a named document: subject
  to the same policy check and the same provenance rules.
- **FR-003**: The skill MUST support at least the formats `ingest` reads: PDF, Word
  (`.docx`), markdown and plain text.

**Policy gate**

- **FR-004**: The skill MUST NOT read a document, or use pasted document text, until the
  model-use policy is settled in the session.
- **FR-005**: When the policy is `unconfirmed` and stays so, the skill MUST NOT read the
  document and MUST continue with the plain interview.
- **FR-006**: When the policy is `restricted`, the skill MUST show the recorded restrictions
  and MUST read the document only after the consultant confirms, in the session, that it
  is permitted.
- **FR-007**: When the policy is `allowed`, the skill MAY read the document without further
  confirmation.

**Using the document**

- **FR-008**: After reading a document, the skill MUST tell the consultant which interview
  topics it found material for and which it did not.
- **FR-009**: For each covered topic, the skill MUST show the drafted answer and ask the
  consultant to confirm, correct or skip it. Nothing drawn from a document MUST be written
  without that confirmation.
- **FR-010**: Topics the document does not cover MUST be asked with the usual prompts. The
  existing topic order, one-topic-at-a-time rule, and save-as-you-go rule still apply.
- **FR-011**: The skill MUST NOT treat a statement in the document as an `active` item, as
  `client-ready`, or as confirmed evidence. Everything written stays `proposed` and
  `internal`, as today.

**Provenance**

- **FR-012**: Each item drawn from a document and confirmed by the consultant MUST be
  recorded with origin `consultant-note`, and its confidence reason MUST name the document
  (file name, or "pasted text" with the consultant's description of it), for example
  "From the SOW (sow-2026-10.pdf), confirmed by the consultant". The skill MUST NOT cite a
  source ID or write `origin: client-document` (charter FR-019 and Constitution Principle
  III are unchanged).
- **FR-013**: Items the consultant substantially rewrites MUST be recorded as
  `consultant-note`. Kept skill suggestions remain `llm-inference`.
- **FR-014**: The end summary MUST name each document used and the topics drawn from it.

**Safety rules carried forward**

- **FR-015**: The skill MUST NOT modify, move, rename or delete any document it reads,
  wherever it is.
- **FR-016**: The skill MUST write only the client label when a code name is in use, even
  if the document names the client.
- **FR-017**: The skill MUST continue to refuse web search, fetch tools and prior-art or
  library skills.
- **FR-018**: The skill MUST NOT read `engagement.md` directly, and MUST NOT browse, list
  or search `10-sources/`. It reads only the specific file in `10-sources/raw/` that the
  consultant names.

**Revision mode**

- **FR-019**: In revision mode, the skill MUST propose only the differences between the
  document and the current charter, and each confirmed change MUST follow the change
  convention with the document named as the trigger.

**Consistency**

- **FR-020**: The charter skill's description, rules list and reference files, the 002
  charter spec requirements that this feature replaces (FR-006 and the related
  acceptance scenario), and the existing evaluation scenarios that expect a refusal MUST
  be updated so that no instruction still tells the skill to refuse every document.

### Key Entities

- **Engagement document**: a document the consultant offers to `charter` (SOW, brief,
  proposal, change order), as a file or as pasted text. Read only; never stored or altered
  by `charter`.
- **Drafted answer**: the skill's reading of one interview topic from a document, shown to
  the consultant and written only once confirmed or corrected.
- **Charter items**: scope entries, questions, hypotheses, assumptions, stakeholders and
  lenses, as defined in the 002 charter spec, now with document provenance where relevant.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With a SOW that covers objectives, boundaries, deliverables and timeline, the
  consultant answers at least 4 of the 10 interview topics by confirmation alone, with no
  retyping.
- **SC-002**: A first charter session that uses a SOW takes at most half the consultant
  turns of the same session without it.
- **SC-003**: In test runs, a document or pasted document text is read zero times when the
  policy is `unconfirmed`, and zero times under `restricted` without the consultant's
  confirmation.
- **SC-004**: 100% of items drawn from a document carry the provenance defined in FR-012,
  and 0 items are written without the consultant's confirmation.
- **SC-005**: In test runs, the skill no longer rejects a permitted document or pasted
  document text.
- **SC-006**: All existing charter rules (IDs, no deletions, code name, `proposed` status,
  no client-ready) still pass their existing tests.

## Assumptions

- The model-use policy is the right gate for reading documents in `charter`; no extra
  per-document consent is needed when the policy is `allowed`.
- Under `restricted`, the consultant is best placed to judge whether a given document
  falls within the restrictions; the skill does not try to judge this itself.
- Reading a document does not require it to be ingested first; `charter` may run before
  `ingest`, as today.
- `charter` does not keep a copy of the document; making it a numbered source remains the
  job of `ingest`.
- The interview topics, formats and helper script behavior from the 002 charter spec are
  unchanged except where stated here.
- Evaluation fixtures use synthetic documents only (Principle VIII).
