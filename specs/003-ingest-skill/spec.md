# Feature Specification: Ingest Skill

**Feature Branch**: `003-ingest-skill`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "Create the spec for the ingest functionality. It should be able to ingest PDFs, and source markdown files - e.g., Documents from clients, transcripts from meetings, or summaries provided by others from meetings and sessions with clients."

## Clarifications

### Session 2026-11-05

- Q: Which file formats are in scope beyond PDF and markdown? → A: Also plain text
  (`.txt`), caption files (`.vtt`, `.srt`) and Word documents (`.docx`). Slide decks,
  spreadsheets, images, web pages and audio are left to later versions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest a client PDF or Word document (Priority: P1)

The client sends the consultant a PDF or Word document, such as an operations review or a
process manual. The consultant puts it in `10-sources/raw/` and runs `ingest`, adding a line of context: who
provided it, when, and why it matters. The skill gives the source the next free `S-###`
ID and writes one markdown file to `10-sources/extracted/`. That file holds the document's
text page by page, tables kept as tables, and a written description of each chart or
diagram, marked as derived. Pages read by OCR are also marked as derived, and passages it
could not read reliably are listed. A row is added to the source index. The original PDF is
left exactly as it was.

**Why this priority**: Ingest is stage 2 of the pipeline, and client documents are the
main evidence in most engagements. `extract-observations` can't cite anything until a
source exists as extracted markdown with stable page locators.

**Independent Test**: In a synthetic engagement with `model_use: allowed`, put three synthetic
PDFs in `10-sources/raw/`: a text PDF with a table and a chart, a scanned PDF, and a PDF
with a page that is hard to read, plus a synthetic Word document with headings, a table
and an embedded chart. Run `ingest`. Confirm that `S-001` to `S-004` exist in
`10-sources/extracted/`. The PDFs have page markers, and the Word document keeps its
headings. Each table is a markdown table, and each chart is described and marked as
derived. The scanned pages are marked as OCR, and the hard page is listed as uncertain. The
index has four rows. Confirm the originals are byte-identical to before.

**Acceptance Scenarios**:

1. **Given** a text PDF in `10-sources/raw/`, **When** the consultant runs `ingest`, **Then**
   an `S-###` file holds the document's text word for word, with a marker for every page,
   so any passage can be cited by page.
2. **Given** a PDF containing a table, **When** it is ingested, **Then** the table appears as
   a markdown table with the same rows, columns and values, not as prose.
3. **Given** a PDF containing a chart, diagram or photo, **When** it is ingested, **Then** the
   extracted file holds any text read from the image and a written description of it, both
   marked as derived, at the page where it appears.
4. **Given** a scanned PDF with no text layer, **When** it is ingested, **Then** its text is
   read by OCR, the source is recorded as derived with method OCR, and every passage the
   skill could not read reliably is listed with its page.
5. **Given** the consultant gives context (who provided it, the date, why it matters, how far
   to trust it), **When** the source is written, **Then** that context is recorded in the
   source's metadata, and its origin is `client-document`.
6. **Given** several new files in `10-sources/raw/`, **When** the consultant runs `ingest`
   with no arguments, **Then** the skill lists every file not yet ingested, asks for a line
   of context for each, and ingests them one after another.
7. **Given** a Word document, **When** it is ingested, **Then** its text is kept word for
   word with its headings, so passages can be cited by section, its tables are markdown
   tables, and each embedded chart, diagram or photo is described and marked as derived.

---

### User Story 2 - Ingest meeting transcripts, meeting summaries and text documents (Priority: P1)

After a client meeting, the consultant has a transcript exported from the meeting tool (as
markdown, plain text or a caption file), or a summary someone else wrote, such as a
colleague's notes or the client's minutes. Some client documents also arrive as markdown
or plain text. The consultant puts them in `10-sources/raw/` and runs `ingest`. A
transcript is split into speaker turns, each with the speaker and a timestamp or turn
number. A summary records who wrote it, when the meeting took place and who attended, and
is clearly marked as a second-hand account. A markdown document keeps its headings, so
passages can be cited by section.

**Why this priority**: Interviews and meetings are the other half of the evidence, and the
source of most of what stakeholders actually think. Transcripts and summaries already come
as text, so they are the cheapest sources to ingest and the first ones the Phase 1 trial
needs.

**Independent Test**: Put a synthetic markdown transcript (three speakers, timestamps), the
same meeting as a `.vtt` caption file, a synthetic meeting summary written by a colleague,
and a synthetic markdown client document in `10-sources/raw/`, and run `ingest`. Check the
results:

- Both transcripts have one entry per speaker turn, with the speaker and timestamp.
- The summary's file records the author, meeting date and attendees, and says it is a
  summary.
- The document keeps its heading structure.
- The text of all four matches the originals word for word.

**Acceptance Scenarios**:

1. **Given** a transcript with speaker labels and timestamps, **When** it is ingested,
   **Then** each speaker turn appears with its speaker and timestamp, and the words of
   every turn are unchanged.
2. **Given** a transcript with no timestamps, **When** it is ingested, **Then** each turn is
   numbered, so it can be cited by turn number.
3. **Given** a transcript whose speakers are generic labels (for example "Speaker 2"),
   **When** it is ingested, **Then** the skill asks the consultant who each speaker is,
   suggests matching people from `00-charter/stakeholders.md`, and records the names the
   consultant confirms next to the original labels, which it leaves unchanged.
4. **Given** a meeting summary written by someone other than the consultant, **When** it is
   ingested, **Then** the source records the author, the meeting date, the attendees if
   known, and that it is a second-hand account, and its origin is `interview-meeting`.
5. **Given** a markdown document from the client, **When** it is ingested, **Then** its
   headings, lists and tables are kept, its text is unchanged, and its origin is
   `client-document`.
6. **Given** notes the consultant wrote themselves, **When** they are ingested, **Then** the
   source's origin is `consultant-note`.
7. **Given** a transcript exported as a caption file (`.vtt` or `.srt`), **When** it is
   ingested, **Then** consecutive caption cues from the same speaker are joined into one
   turn that keeps the first cue's timestamp, and no words are lost or changed.
8. **Given** a plain-text file, **When** it is ingested, **Then** the skill recognizes
   whether it is a transcript (speaker labels) or a document, and a document's
   paragraphs are numbered so they can be cited.

---

### User Story 3 - Model-use policy respected and restricted sources refused (Priority: P1)

Before opening any file, the skill checks the engagement's model-use policy. If the policy
is still `unconfirmed`, it ingests nothing and points the consultant to `charter` to settle
it. If the policy is `restricted`, it shows the recorded restrictions and asks, for each
file, whether that file may be sent to the AI service. A file that may not be sent is never
opened. It is still registered, with only the details the consultant gives, so the rest of
the engagement can refer to it and carry on without its content.

**Why this priority**: Confidentiality is non-negotiable (Principle VIII). Ingest is the first
skill that reads client material, so it is where the model-use policy is enforced. The
constitution requires ingest to refuse restricted sources while the engagement continues.

**Independent Test**: Run `ingest` on synthetic engagements whose policy is `unconfirmed`,
`restricted` and `allowed`, each with the same files in `10-sources/raw/`, one of which
contains a canary string. Under `unconfirmed`, confirm no file is opened and nothing is
written. Under `restricted`, mark the canary file as restricted when asked, and confirm the
canary appears nowhere in the session or the engagement, while that file still has a
registered `S-###` with `restricted: true` and no content.

**Acceptance Scenarios**:

1. **Given** the policy is `unconfirmed`, **When** the consultant runs `ingest`, **Then** no
   file is opened, nothing is written, and the skill says to settle the policy with
   `charter` first.
2. **Given** the policy is `restricted`, **When** the consultant runs `ingest`, **Then** the
   skill shows the recorded restrictions and asks for each file whether it may be sent,
   before opening any of them.
3. **Given** the consultant says a file may not be sent, **When** the skill continues,
   **Then** the file is never opened, and a source record is written with
   `restricted: true`, the details the consultant gave (title, type, date, provider) and no
   extracted content.
4. **Given** the policy is `allowed`, **When** the consultant says a particular file must not
   be sent, **Then** it is handled as restricted in the same way.
5. **Given** the engagement uses a client code name, **When** the skill writes titles,
   summaries and index rows, **Then** it uses the code name. The extracted content itself
   stays word for word, because it stays inside the engagement folder.
6. **Given** any source, **When** it is ingested, **Then** no engagement content is sent to any
   service other than the consultant's AI assistant.

---

### User Story 4 - Spot-check, correct and approve an extraction (Priority: P2)

After ingesting, the consultant spot-checks the parts most likely to be wrong. The skill
shows them the derived content (OCR pages, chart and diagram descriptions), the tables and
the uncertain passages for each new source. The consultant approves a source, which makes
it `active`, or points out an error. The skill fixes the passage, keeps the previous text
in the changelog, and lists any observations already citing that source so they can be
checked.

**Why this priority**: "Spot-checks image and table extraction" is the consultant gate for
stage 2. Extraction errors would otherwise flow silently into observations and findings. A
proposed source is still usable for a first pass, so this ranks below ingesting itself.

**Independent Test**: On a synthetic engagement with one ingested PDF that has a known OCR
error, an uncertain passage and a table, run the review. Confirm the skill presents those
three parts, that correcting the OCR error changes only that passage and logs a dated
changelog entry with the previous text, and that approving the source sets it to `active`
and updates its index row, and nothing else changes.

**Acceptance Scenarios**:

1. **Given** newly ingested sources, **When** the consultant asks to review them, **Then**
   the skill shows, per source, the derived passages, the tables and the uncertain passages,
   each with its locator.
2. **Given** the consultant approves a source, **When** the skill applies it, **Then** its
   status becomes `active` in both the source file and the index.
3. **Given** the consultant reports an extraction error and gives the correct text, **When**
   the skill applies it, **Then** only that passage changes, the passage is removed from
   the uncertain list if it was there, and the changelog records the date, the source ID,
   the locator, the previous text and the reason.
4. **Given** observations already cite a corrected source, **When** the correction is
   applied, **Then** the skill lists them by ID so the consultant can check them.
5. **Given** the consultant gives no instruction on a source, **When** the review ends,
   **Then** it stays `proposed`.

---

### Edge Cases

- The skill is run outside an engagement folder: it stops and explains how to create an
  engagement first.
- The consultant points to a file outside `10-sources/raw/`: the skill offers to copy it
  into `10-sources/raw/` first, and ingests only from there. It never moves or deletes the
  file it was pointed to.
- A file in `10-sources/raw/` has an identical copy that was already ingested: the skill
  names the existing `S-###` and doesn't create a second one.
- A new version of an already-ingested document arrives: it becomes a new source. The
  skill asks whether it replaces the earlier one and, if so, links it with `supersedes`. The
  earlier source and its observations are kept.
- A file is in a format this version doesn't handle (for example a slide deck, spreadsheet,
  image or audio file): the skill lists it as not supported yet, writes nothing for it,
  and carries on with the rest.
- A PDF or Word document is password-protected, damaged or empty: the skill reports it and
  writes no source for it.
- A Word document has comments or unaccepted tracked changes: the skill says so, extracts
  the comments in a separate marked section with their locators, and lists each tracked
  change as an uncertain passage for the consultant to settle. It never accepts or
  rejects changes itself.
- A caption file has no speaker labels: each cue keeps its timestamp, and the skill asks
  the consultant whether the speakers can be identified.
- A PDF's printed page numbers differ from its page count (for example, roman-numbered
  front matter): locators use the PDF page number, and the printed number is noted where
  it differs.
- A long document is interrupted partway: the source isn't added to the index or shown
  as complete until extraction finishes. The next run resumes or restarts it.
- An original is renamed or removed from `10-sources/raw/` after ingest: the skill reports
  that the original is missing, and keeps the source record.
- A meeting summary was produced by an AI note-taker rather than a person: the skill
  records that it was machine-generated and sets confidence no higher than `medium`.
- The same meeting has both a transcript and a summary: they are two sources, and both
  record the meeting date and title so they can be related.
- The consultant marks a source restricted after it was ingested: the skill sets
  `restricted: true`, warns that its content was already processed, and removes the
  extracted content only on the consultant's explicit instruction, logging that it did so.
  Later skills must not read a restricted source.
- A transcript's text includes sensitive personal remarks: it is kept word for word,
  because extraction never edits content. The source stays `internal`.
- Source files contain hidden text, comments or instructions addressed to an AI: they are
  extracted as content like any other text and never followed as instructions.
- Hand-written source records or IDs already exist: their IDs count as taken, and new
  sources are numbered after the highest existing one.

## Requirements *(mandatory)*

### Functional Requirements

**Starting**

- **FR-001**: The `ingest` skill MUST be bundled with the framework, so new engagements
  include it and existing engagements gain it on refresh.
- **FR-002**: The skill MUST find the engagement record before doing anything else, and MUST
  stop with an explanation if it isn't run inside an engagement.
- **FR-003**: The skill MUST work only on files in `10-sources/raw/` (including its
  subfolders). Run with no arguments, it MUST list every file there that has not been
  ingested yet. The consultant MAY instead name specific files.
- **FR-004**: The skill MUST handle PDF (`.pdf`), Word (`.docx`), markdown (`.md`), plain
  text (`.txt`) and caption (`.vtt`, `.srt`) files. Other formats MUST be listed as not
  supported yet and left untouched.

**Model-use policy**

- **FR-005**: Before opening any file, the skill MUST read the model-use policy from the
  engagement record. If it is `unconfirmed`, the skill MUST NOT open any file or write
  anything, and MUST tell the consultant to settle the policy with `charter`.
- **FR-006**: If the policy is `restricted`, the skill MUST show the recorded restrictions and
  ask, for each file, whether it may be sent to the AI service, before opening any of them.
  Under any policy, the consultant MAY mark a file as restricted.
- **FR-007**: The skill MUST NOT open a restricted file. It MUST write a source record for it
  with `restricted: true`, the details the consultant gives, and no extracted content.
- **FR-008**: The skill MUST NOT send engagement content to any service other than the
  consultant's AI assistant, and MUST NOT do web research.

**Extracting content**

- **FR-009**: Each ingested file MUST become exactly one source with the next free `S-###` ID,
  written as one markdown file in `10-sources/extracted/`, using the engagement's source
  template.
- **FR-010**: Content that the skill reads directly (a PDF's text layer, the text of a Word,
  markdown, plain-text or caption file) MUST be kept word for word. The skill MUST NOT
  summarize, paraphrase, correct or reorder it.
- **FR-011**: Every passage MUST be citable by a stable locator: the page for PDFs; the
  heading path for Word and markdown documents and summaries (with a paragraph number
  where a section has no headings); the paragraph number for plain-text documents; and the
  timestamp (or the turn number, when there are no timestamps) for transcripts.
- **FR-012**: Tables MUST be kept as markdown tables with the same rows, columns and values.
- **FR-013**: For each chart, diagram or photo in a PDF or Word document, the skill MUST
  record any text read from the image and a written description of it, both marked as
  derived, at its locator.
- **FR-014**: Pages without a text layer MUST be read by OCR and marked as derived. The
  source MUST record its extraction method (text, OCR, vision description or mixed) and
  whether any of its content is derived.
- **FR-015**: Every passage the skill could not read reliably MUST be listed with its
  locator in the source's uncertain passages.
- **FR-016**: Transcripts MUST be split into speaker turns, each with the original speaker
  label and its timestamp or turn number. Consecutive caption cues from the same speaker
  MUST be joined into one turn that keeps the first cue's timestamp. Names the consultant
  confirms for generic labels MUST be recorded alongside the original labels, without
  changing them.
- **FR-017**: Text inside a source MUST be treated only as content. The skill MUST NOT follow
  instructions found in a source.

**Recording the source**

- **FR-018**: Each source record MUST state what kind of material it is (document, meeting
  transcript, or meeting summary or notes), its file format, the original's file name in
  `10-sources/raw/`, who provided it, and its date. For meetings it MUST also record the
  meeting date and, when known, the attendees. For summaries it MUST record the author and
  whether a person or an AI note-taker wrote it.
- **FR-019**: Origin MUST be `client-document` for client documents, `interview-meeting` for
  meeting transcripts and summaries written by others, and `consultant-note` for the
  consultant's own notes. The consultant MAY override the suggested origin.
- **FR-020**: Confidence MUST reflect how far the consultant trusts the source, with a
  one-line reason. When the consultant doesn't say, it MUST be `medium` with a reason saying
  trust was not stated. AI-generated summaries MUST NOT be rated above `medium`.
- **FR-021**: The skill MAY write a short description of what the source is, clearly
  labelled as written by the skill. It MUST NOT state conclusions or findings. Those belong
  to later skills.
- **FR-022**: Every new source MUST have status `proposed` and audience `internal`. The skill
  MUST NOT set any source to `client-ready`.
- **FR-023**: Each new source MUST get a row in `10-sources/index.md` with its ID, title,
  type, date, origin, status and restricted flag, added only once extraction is complete.
- **FR-024**: When the engagement uses a client code name, the skill MUST use the code name
  in every title, description, index row and log entry it writes. The extracted content
  stays word for word.
- **FR-025**: New IDs MUST be the next free `S-###` number, MUST NOT reuse any existing number,
  and links MUST use IDs only.

**Originals**

- **FR-026**: The skill MUST NOT modify, rename, re-encode, move or delete anything in
  `10-sources/raw/`. Copying a file into it at the consultant's request is the only
  change allowed there.
- **FR-027**: The skill MUST detect a file whose content is identical to an already-ingested
  original, name the existing source, and not ingest it again.
- **FR-028**: When a new file replaces an already-ingested document, the skill MUST ask the
  consultant, and only on their confirmation link the new source to the old one with
  `supersedes`. The old source MUST be kept.

**Review and correction**

- **FR-029**: On request, the skill MUST present, per source, the derived passages, the tables
  and the uncertain passages, each with its locator, for the consultant to spot-check.
- **FR-030**: The skill MUST change a source's status only on the consultant's explicit
  instruction (approve → `active`, reject → `rejected` with a reason), and MUST update the
  index row to match.
- **FR-031**: When the consultant reports an extraction error, the skill MUST change only that
  passage, MUST log the date, source ID, locator, previous text and reason in
  `60-log/changelog.md`, and MUST list by ID every observation that cites that source.

**Wrap-up**

- **FR-032**: At the end of each session, the skill MUST show a summary listing the sources
  written (by ID and title), files registered as restricted, files skipped and why, sources
  with derived or uncertain content to spot-check, and next steps (review the sources, then
  run `extract-observations`).

### Key Entities

- **Original**: A file as received, kept unchanged in `10-sources/raw/`. The final authority
  for every citation.
- **Source (`S-###`)**: One extracted original in `10-sources/extracted/`: its metadata
  (kind of material, format, original's file name, provider, date, origin, confidence,
  extraction method, derived flag, restricted flag, uncertain passages, status) and its
  content, with locators. One original makes exactly one source.
- **Source index**: The table in `10-sources/index.md`, one row per source.
- **Locator**: How a passage is cited: a page, a heading path, a timestamp or a turn number.
- **Derived passage**: Content the skill produced rather than read verbatim (OCR text, a
  description of a chart, diagram or photo), always marked as derived.
- **Speaker turn**: One speaker's continuous contribution in a transcript, with the original
  label, any confirmed name, and its timestamp or turn number.
- **Model-use policy**: `allowed`, `restricted` or `unconfirmed`, with the recorded
  restrictions. Read from the engagement record. It decides whether files may be opened.
- **Change event**: A dated changelog entry. For ingest, it records a correction to an
  extracted passage, or the removal of a restricted source's content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of test runs, every original in `10-sources/raw/` is byte-identical
  before and after ingest.
- **SC-002**: In test runs, zero files are opened while the policy is `unconfirmed`, and zero
  restricted files are opened under any policy, as shown by a canary string that appears
  nowhere in the session or the engagement.
- **SC-003**: 100% of the sources the skill writes carry a unique ID, kind of material,
  format, original file name, origin, confidence with a reason, extraction method, derived
  and restricted flags, status `proposed` and audience `internal`, as confirmed by an
  automated check.
- **SC-004**: On the synthetic test set, 100% of sampled passages from text PDFs and from
  Word, markdown, plain-text and caption files match the original word for word.
- **SC-005**: On the synthetic test set, 100% of tables keep their rows, columns and values,
  100% of charts and diagrams have a description marked as derived, and 100% of PDF pages,
  document sections and transcript turns can be cited by locator.
- **SC-006**: A consultant spends under 20 minutes of hands-on time (context and spot-check)
  to ingest a typical batch of 10 sources.
- **SC-007**: On the Phase 1 trial engagement (held locally and anonymized), every source in a
  supported format is ingested, and the lead consultant judges at least 90% of them usable
  for extracting observations without correction.
- **SC-008**: Zero sources become `active` or `rejected` without an explicit consultant
  instruction, and zero become `client-ready`.

## Assumptions

- Engagement initialization (001) and the charter skill (002) are in place. The engagement
  record holds the model-use policy and its notes, and the source template and source index
  exist in the formats they define. Ingest may need to extend the source template (for
  example, to record kind of material, meeting date, attendees and author); any such
  change updates every template and skill that uses it, as the constitution requires.
- The consultant puts originals in `10-sources/raw/` themselves. Ingest does not fetch files
  from email, shared drives or meeting tools.
- Transcripts are already text, produced by a meeting tool or a person. Transcribing audio
  or video is out of scope.
- Slide decks, spreadsheets, images, web pages and audio are left to later versions of
  this skill. The constitution's rules for spreadsheets and image files apply when those
  formats are added. Older Word files (`.doc`) and other text-like formats (`.rtf`,
  `.html`) are also out of scope. The consultant can save them as `.docx` or `.pdf` first.
- Sources are mostly in English. Content in other languages is kept as it is; translation
  is out of scope.
- A typical engagement has 10–20 sources (requirements draft). Very long documents are
  supported but may take more than one session.
- The skill runs inside the consultant's supported AI assistant (Claude Code initially),
  which is the only AI service it uses. Sending a file to it counts as sending it to an
  external AI service for model-use purposes.
- A restricted source is registered with only what the consultant says about it. The
  consultant can still record what they learned from it as their own notes, and the rest
  of the engagement proceeds without its content.
- Ingest does not extract observations, tag sources to questions, or judge what a source
  means. That is `extract-observations` and later skills' work.
- One consultant runs `ingest` at a time per engagement.
- Validation uses synthetic sources in the repository, plus the Phase 1 trial engagement
  held locally and anonymized, never committed (Principle VIII).
