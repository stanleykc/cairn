# Research: Ingest Skill

Decisions for the `ingest` skill. Each one resolves an open point in the plan's Technical
Context or a design choice the spec leaves open. Numbering restarts for this feature (R1,
R2, …). "002 R7" means decision R7 of the charter feature.

## R1. What the skill is made of

- **Decision**: One Claude Code skill folder, `src/cairn/assets/skills/ingest/`, holding:
  - `SKILL.md`: the session flow, the hard rules and the never-do list (about 250 lines).
  - `reference/`: per-format guidance (`formats.md`), the source file format and field
    rules (`source-record.md`), the review and correction flow (`review-and-correct.md`),
    and a byte-identical copy of the shared `change-convention.md`.
  - `scripts/ingest.py`: one standard-library helper script (Python 3.9+).
  `cairn init` and `cairn refresh` already copy every bundled skill and generate
  `.claude/settings.json` from its `Bash(...)` rules (001 R10, 002 R21), so FR-001 needs
  no command change.
- **Rationale**: Same shape as `charter`, which works. Per-format detail is only loaded
  when a file of that format is being ingested.
- **Alternatives considered**: One skill per format (`ingest-pdf`, `ingest-transcript`).
  The framework design names one `ingest` skill, and the policy check, numbering and index
  must be shared anyway.

## R2. What the script does, and what the assistant does

- **Decision**: The script writes every word that must be verbatim. The assistant only
  adds what needs judgment or vision, and the script then checks that it didn't disturb
  the verbatim text.

  | Job | Done by | Why |
  |---|---|---|
  | Find the engagement, read the policy and code name | script `status` | Deterministic. Keeps `engagement.md` out of the conversation (002 R7). |
  | List files in `raw/` and their state; next free `S-###` | script `status` | ID assignment is a script job (Principle I). |
  | Refuse to extract under `unconfirmed`, or under `restricted` without per-file consent | script `extract` | Second layer behind the instructions (R6). |
  | Write the text layer of a PDF (when poppler is present, R4), the text of Word, markdown, plain-text and caption files, page markers, paragraph and turn numbers, Word tables, comments and tracked changes | script `extract` | FR-010 and SC-004 need 100% word-for-word. Copying long text through the model risks silent slips and costs output tokens. Without poppler, the assistant copies the PDF text, and the source is marked `fidelity: unchecked`. |
  | Duplicate check by content hash | script `extract` | Deterministic (FR-027). |
  | Turn PDF table text into markdown tables | assistant | Needs the page image to see the grid. |
  | OCR of pages with no text layer; text and description of charts, diagrams, photos | assistant (vision) | Needs vision. Always marked derived. |
  | Uncertain passages | assistant, plus script flags (low-text pages, tracked changes, unreadable images) | Mostly judgment. |
  | Metadata: title, material, origin, provider, dates, attendees, author, confidence, context, description | assistant, from the consultant | Conversation. |
  | Check fields, markers, word-for-word fidelity, code-name leaks | script `verify` | Deterministic, run after every write. |
  | Mark complete and add the index row; status changes; restrict; refs | script `finalize`, `set-status`, `restrict`, `refs` | Two files (source + index, sometimes the changelog) must change together. |
- **Rationale**: Same split as 002 R2, pushed further, because ingest's content must be
  verbatim and is far longer than charter entries.
- **Alternatives considered**:
  - *The assistant transcribes everything it reads.* Simple, but a 60-page PDF becomes
    60 pages of model output with no way to prove it matches (SC-004).
  - *The script does everything, including OCR and descriptions.* Needs an OCR engine and
    can't describe charts.

## R3. Where the script lives and which Python it needs

- **Decision**: Same as 002 R3. It lives at `skills/ingest/scripts/ingest.py` and runs as
  `python3 <skill base directory>/scripts/ingest.py <command>`, standard library only,
  Python **3.9+**, no import of `cairn` or of `charter.py`.
- **Shared parsing code**: `ingest.py` copies the parts of `charter.py` it needs (front
  matter and entry parsing, finding the engagement, redaction, atomic write). A parity
  unit test runs both parsers on the same inputs and asserts the same results. Extracting a
  shared module is deferred until a third skill needs the same code (see Complexity
  Tracking in the plan).
- **Alternatives considered**: Importing `../../charter/scripts/charter.py` by path. Skills
  are refreshed and may be removed independently, so a cross-skill import can break.
  A byte-identical shared module in both skills. It's cleaner, but it means refactoring
  `charter.py` in this feature.

## R4. Reading PDFs: poppler when present, the assistant's own reading otherwise

- **Decision**: Poppler is **optional**. The script checks for it on every run, and
  `status` reports `pdf_backend.available`.
  - **With poppler (checked mode)**: the script runs these tools locally:
    - `pdftotext -enc UTF-8 <file> -` for the text layer. The output is split into pages
      on form feeds, and each page is written under its page marker.
    - `pdfinfo` for the page count, and to detect encrypted or damaged files.
    - `pdfimages -list` for which pages hold images. This tells the assistant which pages
      need a description.
    `verify` compares the content with the text layer word for word (R11), and the source
    gets `fidelity: checked`.
  - **Without poppler (unchecked mode)**: `extract` still runs the policy gate, the hash
    and the duplicate check. It also does a standard-library check of the PDF: the
    `%PDF-` header, an `/Encrypt` entry in the trailer, and an estimated page count from
    the `/Type /Page` objects. It then writes the skeleton: front matter and empty content
    markers, with `fidelity: unchecked`. The assistant reads the pages with Read and
    writes each page's text-layer text under its `### p. n` marker, copying it as
    exactly as it can, plus the same tables, OCR and description callouts as in checked
    mode. It sets `page_count` from what Read reports. `verify` checks the structure
    (every page from 1 to `page_count` has a marker) but can't compare words. It warns
    `fidelity-unchecked` instead.
  - Unchecked sources are flagged in the end summary and put first in review. The review
    shows a sample of their text pages next to the page image for the consultant to
    compare (FR-029). The install hint (`brew install poppler`, `apt install
    poppler-utils`) is shown once per session, as a suggestion, never as a blocker.
  - If Read can't open a PDF that passed the header check, the in-progress source is
    rejected with reason "unreadable" (`set-status … rejected` is allowed on in-progress
    sources). It gets no index row, and its ID isn't reused. `status` then shows the
    original as `rejected`, and `extract` refuses it (exit 6), so later runs skip it.
- **Vision (both modes)**: The assistant views every page with the Read tool (`pages`, at
  most 20 per request). It rebuilds tables, OCRs pages without text and describes images
  there. Pages are processed in order, and `pages_reviewed` records progress, so a long
  document resumes where it stopped (R12).
- **Rationale**: Claude Code already reads PDFs, so nobody is blocked by a missing
  install. Where poppler is present (one command on a Mac), the word-for-word guarantee
  (FR-010, SC-004) is proven automatically. Where it isn't, the source records that it
  wasn't, and the consultant's review covers the gap. `pdftotext` is the standard,
  well-tested text-layer extractor. It's local, and the script stays standard-library
  Python.
- **Alternatives considered**:
  - *Poppler required.* The strongest guarantee, but a missing install blocks every PDF.
  - *Agent only.* The simplest option, but it drops the automated fidelity check for every
    PDF, and long PDFs cost a full document of output.
  - *macOS PDFKit via `osascript -l JavaScript`.* It doesn't work on Linux, and it would
    add a third PDF path to test.
  - *`tesseract` for OCR.* An extra install that does no better than vision on typical
    scans, and the result is marked derived either way. The spec's "read by OCR" is met by
    vision OCR, recorded as `extraction_method: ocr`.
- **Verify during implementation**:
  - Whether Claude Code's Read of a PDF page range itself needs poppler. If it does,
    unchecked mode is limited to PDFs that Read can open without `pages`, and longer PDFs
    are skipped with the install hint.
  - How well the page-count estimate holds up on the synthetic fixtures. It's only used
    until Read reports the real count.

## R5. Reading Word documents

- **Decision**: The script parses `.docx` itself with `zipfile` and `xml.etree`:
  - Paragraphs in document order. `Title` and `Heading 1`–`Heading 6` styles become
    markdown headings, keeping their level. List paragraphs (`numPr`) become `-` or `1.`
    items. Text boxes are written where they're anchored.
  - Tables become markdown tables. Merged cells (`gridSpan`, `vMerge`) repeat the cell
    value and add an uncertain passage. A nested table is flattened into its cell and
    flagged as uncertain.
  - Footnotes and endnotes go at the end of the content, under a marker.
  - Comments (`comments.xml`) go in a separate marked section. Each one gets the locator
    of the paragraph it's anchored to, its author and its date.
  - Tracked changes are kept inline in CriticMarkup (`{++inserted++}`, `{--deleted--}`),
    and each one is listed as an uncertain passage. The script never accepts or rejects a
    change (spec edge case).
  - Images (`a:blip`) become a placeholder where they appear. The image file is copied to
    the work folder (R13) for the assistant to view and describe. EMF and WMF images can't
    be viewed, so they're listed as uncertain.
  - Embedded charts (`c:chart`) are written as a **derived** markdown table built from
    the chart's cached series values, with its title. The assistant adds a description.
    SmartArt text (`dgm`) is written as a derived list.
  - Headers and footers are skipped. Their text repeats on every page and has no locator.
  Password-protected (OLE container), damaged or empty files are reported as
  `unreadable`, and no source is written.
- **Rationale**: Word XML holds the exact text, the heading styles and the table grid, so
  every part except images can be extracted deterministically and checked exactly.
- **Alternatives considered**: `textutil` and `pandoc`. `textutil` is macOS-only and drops
  heading levels. `pandoc` is an extra install and doesn't mark tracked changes or comments
  the way the spec needs.

## R6. Enforcing the model-use policy (FR-005–FR-008, SC-002)

- **Decision**: Four layers, as in 002 R6:
  1. **Instructions.** `SKILL.md` puts the policy check first in the never-do list: run
     `status` first, and under `unconfirmed` open nothing. Never Read a file in `raw/`
     before the consultant has said it may be sent (under `restricted`), and never Read one
     marked restricted.
  2. **The script gates extraction.** `extract` exits with code 3 under `unconfirmed`. Under
     `restricted` it requires `--sendable`, which the skill passes only after the
     consultant's yes for that file. `register-restricted` never opens the file: it records
     only the path, its size from `stat` (`raw_bytes`) and the details the consultant gave.
     No hash is taken, so "never opened" holds literally.
     Because there is no hash, a renamed copy of a restricted file can't be found by
     content. `status` therefore flags a new file as `possible_restricted_copy` when its
     size equals a restricted record's `raw_bytes`, or its name stem matches one once
     version suffixes are stripped (R15). `extract` refuses such a file without
     `--sendable` under every policy (exit 3, `possible-restricted-copy`), and the skill
     asks the consultant first. A size match can be a false positive. The cost is one
     extra question, which is the safe direction.
  3. **The script's output is metadata only.** `status`, `extract` and `review` print
     counts, locators, labels and paths, never extracted text. The assistant sees content
     only by reading the `S-###` file after `extract`, which happens only for sendable
     files.
  4. **Tested.** A unit test makes the restricted file unreadable (`chmod 000`) and asserts
     that every command still succeeds. The skill evaluation uses a canary string in the
     restricted file and asserts it appears nowhere in the transcript or in any written
     file (SC-002).
- **Rationale**: Claude Code can't deny a tool per file, so the instructions and the script
  together give two independent barriers, and the tests prove both.
- **Alternatives considered**: A `PreToolUse` hook that blocks Read under `10-sources/raw/`.
  It can't tell a sendable file from a restricted one without shared state that the script
  would have to maintain. Revisit if evaluations show the instruction layer slipping.

## R7. The extracted source file

- **Decision**: One markdown file per source, with front matter from the source template
  (R8), then fixed body sections. The extracted text sits between two markers:

  ~~~text
  ## Context
  ## Description
  ## Speakers            (transcripts only)
  ## Uncertain passages
  ## Extracted content
  <!-- cairn:content:start -->
  …verbatim content, with locator markers, tables and callouts…
  <!-- cairn:content:end -->
  ~~~

  - The original headings of a Word or markdown document are kept at their original
    level, inside the markers. Heading paths are computed from them, so they're never
    renumbered or demoted.
  - **Locator markers** (written by the script):
    - PDF: `### p. 7`, or `### p. 7 (printed: iv)` when the printed number differs.
    - Plain text, and markdown sections with no headings: a `[¶12]` prefix.
    - Transcripts: `**Speaker 2** [T17 · 00:14:32]:` (or `[T17]` when there are no
      timestamps).
  - **Callouts** (Obsidian syntax, readable as blockquotes anywhere):
    - `> [!derived] ocr | vision-description | chart-data | diagram-text` for content the
      skill produced.
    - `> [!corrected]` for a passage fixed in review (R11).
    - `> [!comment]` for Word comments.
  - The skill's own **Description** is labelled in the text "Written by `ingest`. Not part
    of the source." Observations must not cite it (FR-021).
  The full format is in [contracts/source-file.md](contracts/source-file.md).
- **Rationale**: The markers let `verify` compare exactly the verbatim region with the
  original. Keeping the original heading levels means the content is unchanged, and the
  heading path stays a stable locator.
- **Alternatives considered**: Demoting the original headings under `## Extracted content`.
  It changes the content, and a level-5 heading can't go two levels deeper. A sidecar
  file per source (`S-###.content.md`). That breaks "one source, one file" (FR-009).

## R8. Changes to the source template and the index

- **Decision**:
  - New field `material`: `document` | `meeting-transcript` | `meeting-notes`, for the
    kind of material (FR-018).
  - `source_type` keeps its meaning as the **file format**. Its values become `pdf` |
    `docx` | `markdown` | `text` | `vtt` | `srt` | `deck` | `spreadsheet` | `image` | `web`
    | `other`, and `transcript` moves to `material`. No engagement has sources yet, so
    nothing needs migrating.
  - New fields: `raw_sha256`, `meeting_title`, `meeting_date`, `attendees: []`, `author`,
    `author_kind` (`person` | `ai-notetaker`), `extraction_status` (`in-progress` |
    `complete`), `page_count`, `pages_reviewed` and `content_removed`.
  - `raw_file` holds the path relative to `10-sources/raw/`, so subfolders work (FR-003).
  - `extraction_method` gains `none`, for restricted records.
  - Body sections as in R7.
  - The index keeps its seven columns. `Type` shows `material`, and `Restricted` shows
    `yes` or `no`.
- **Rationale**: These are the smallest additions that meet FR-018, FR-023 and the
  resume, duplicate and restricted edge cases. Status stays in front matter (Principle I).
- **Alternatives considered**: Renaming `source_type` to `format`. The rename would touch
  the 001 contracts and tests for no gain.

## R9. Transcripts

- **Decision**: The script parses transcripts into speaker turns:
  - **VTT**: cues, with the speaker taken from `<v Name>` voice tags or a leading `Name:`.
  - **SRT**: numbered cues, with the speaker taken from a leading `Name:`.
  - **Markdown and plain text**: the common export shapes, each recognized when most
    non-blank lines match it:
    - `Name: text`
    - `**Name:** text`
    - `[hh:mm:ss] Name: text`
    - `Name  hh:mm:ss` on its own line, followed by the text (Otter, Teams).
    - `Name (hh:mm:ss)`.
  - Consecutive cues or lines from the same speaker are joined into one turn that keeps
    the first timestamp (FR-016). Caption text is joined with single spaces, and no word is
    dropped. Inline caption tags (`<i>`, `<c>`) are kept as written.
  - Turns are always numbered (`T1`, `T2`, …). The locator is the timestamp when the file
    has timestamps, otherwise the turn number (FR-011).
  - Labels such as `Speaker 2`, `Unknown speaker` or `Participant 3` are reported as
    `generic_labels`. The assistant asks who they are, suggests people from
    `00-charter/stakeholders.md`, and writes confirmed names in the `## Speakers` table.
    The labels in the turns never change.
  - A caption file with no speaker labels keeps one turn per cue, labelled `(unlabelled)`.
  - A text file that matches no transcript shape is treated as a document. `extract --as
    transcript` forces transcript parsing. If no shape matches, it fails with
    `transcript-format-unknown` and writes nothing.
- **Rationale**: These shapes cover the meeting tools consultants use (Zoom, Teams, Meet,
  Otter). Parsing deterministically keeps every word and timestamp exact.
- **Alternatives considered**: Letting the assistant split turns. Same objection as R2.

## R10. Plain text and markdown documents

- **Decision**:
  - **Markdown**: copied byte for byte between the content markers, with line endings
    normalized to `\n`. If a top-level section has no heading, its paragraphs get `[¶n]`
    prefixes, so they can be cited (FR-011). A markdown file that already has YAML front
    matter keeps it as content.
  - **Plain text**: paragraphs (blocks separated by blank lines) are numbered `[¶1]`,
    `[¶2]`, …. The text is unchanged otherwise. Because markdown treats single newlines as
    spaces, each paragraph's line breaks are kept by ending lines with two spaces (a
    markdown hard break). `verify` ignores the two spaces.
  - Encoding: UTF-8, then UTF-8 with BOM, then cp1252, in that order. Anything else is
    reported `unreadable`.
- **Rationale**: Markdown and plain text need no interpretation, so the script copies them
  exactly.

## R11. Fidelity check and corrections

- **Decision**: `verify <ID>` re-extracts the original and compares it with the content
  region, one locator unit at a time (PDF page, document section, transcript turn).
  - Words are compared after normalizing whitespace. Locator markers, the two-space hard
    breaks, table pipes and table separator rows are ignored.
  - Outside tables, the words must match in order. Inside markdown tables, cell words are
    compared as a multiset against the rest of that page, because a PDF text layer may list
    table cells in a different order.
  - `[!derived]` callouts are skipped. A `[!corrected]` callout counts as the previous text
    it records (`> was: …`), so the comparison still holds after a review fix.
  - Any difference is reported as `content-mismatch`, with its locator only. Content is
    never printed.
  - A review fix (FR-031) replaces the wrong passage with a `[!corrected]` callout that
    carries the date, the new text and the previous text. The skill also logs an
    `extraction-fix` event (R14).
  - The source's `fidelity` field records the result: `checked` when the comparison ran
    and passed at `finalize`, or `unchecked` for a PDF extracted without poppler (R4).
    Word, markdown, text and caption sources are always `checked`. An unchecked source
    stays unchecked even if poppler is installed later. Re-checking is a possible later
    addition, not part of this feature.
- **Rationale**: This is SC-004 as an automated check. Recording the previous text inside
  the callout lets `verify` hold after a fix without any exception list. The `fidelity`
  field tells later skills and the consultant which sources were proven word for word.
- **Alternatives considered**: Checking a sample of passages only. That's what SC-004
  measures, but an exhaustive check costs nothing extra.

## R12. Interrupted ingests and resuming

- **Decision**: `extract` writes `S-###.md` with `extraction_status: in-progress` straight
  away. The file reserves the ID. No index row is written until `finalize` (FR-023).
  `status` lists in-progress sources. Running `extract` again on the same original returns
  the existing ID with `resumed: true`, and `--restart` rewrites the draft under the same
  ID. For PDFs, `pages_reviewed` records how far the vision pass got. `finalize` runs
  `verify`, sets `extraction_status: complete`, adds the index row and removes the work
  folder.
- **Rationale**: Meets the "interrupted partway" edge case with state in front matter
  (Principle I) and no lock files.

## R13. The work folder

- **Decision**: Images from Word documents are copied to `.cairn/work/ingest/<S-ID>/`
  inside the engagement, for the assistant to view. `finalize` deletes the folder, and
  `status` reports orphaned work folders.
- **Rationale**: The copies stay inside the engagement folder (Principle VIII), never in
  `raw/` (Principle II). `.cairn/` is already the framework's internal folder (001
  manifest), so the canonical layout doesn't change.
- **Alternatives considered**: Keeping the images next to the source
  (`extracted/S-###.assets/`). It's useful for spot-checks, but it duplicates client
  images outside `raw/` for good. Keeping them can be added later if consultants want it.

## R14. Changelog events for sources

- **Decision**: Extend the shared change convention (002 contracts/change-convention.md):
  - `extraction-fix`: a passage of a source was corrected in review. The subject is
    `S-004 @ p. 3`. The detail (the previous text) is required. The trigger is `-`.
  - `restrict`: a source was marked restricted after it was ingested. The trigger is `-`.
  - `remove-content`: a restricted source's content was removed on the consultant's
    instruction. The trigger is `-`.
  - The existing `supersede` (`S-002 → S-007`, logged when the new version is approved)
    and `reject` events apply to sources unchanged.
  - The subject grammar gains the `<ID> @ <locator>` form.
  The convention file is updated in `charter/reference/`, in the 002 contract and in the
  changelog seed. `ingest/reference/` ships an identical copy, and a new test asserts the
  copies are byte-identical (002 R13).
- **Rationale**: `correct` already means "a wrong claim is replaced by a new object". An
  extraction fix edits a passage in place and keeps the old text. Giving it its own event
  keeps `what-changed` able to tell the two apart. The trigger values (new evidence,
  client feedback, rethinking) don't describe a transcription fix, so `-` is used, as for
  `model-use`.

## R15. Status changes, versions and restriction after ingest

- **Decision**:
  - `set-status <ID> active` approves a source. If the source has `supersedes`, the old
    source becomes `superseded`, the new source's `change_reason` and `change_trigger`
    are copied onto it, and a `supersede` event is logged. `set-status <ID> rejected
    --reason … --trigger …` rejects a source and logs `reject`. Both update the index row
    in the same step. Approving never changes `audience`.
  - A new version is a new source with `supersedes: ["<old ID>"]` set only after the
    consultant confirms it (FR-028). The skill suggests a link when the file name matches
    an existing source's `raw_file` once version suffixes (`v2`, `final`, dates) are
    stripped.
  - `restrict <ID> --reason …` sets `restricted: true` and logs `restrict`.
    `--remove-content` also empties the content region, sets `content_removed: true`,
    and logs `remove-content`. Both update the index row. Removing content is the one
    deletion the spec allows, and it's logged.
  - `refs <ID>…` lists objects whose fields cite the IDs (`source`, `derived_from`,
    `supports`, `contradicts`), as IDs and paths only (FR-031).
- **Rationale**: Each of these touches the source, the index and often the changelog. The
  script keeps them in step, as `model-use` does in 002.

## R16. Numbering

- **Decision**: The next `S-###` is one more than the highest `S-` number found in:
  - the `id` fields and file names in `10-sources/extracted/`;
  - the index rows;
  - every Cairn object's fields and body outside `10-sources/`;
  - the changelog.
  The script never reads `raw/`, and never counts numbers inside content regions, where a
  client document may contain strings such as `S-104` that aren't Cairn IDs. Duplicates and
  malformed IDs are reported, never fixed (spec edge case for hand-written IDs).
- **Rationale**: Follows 002 R9, adapted to ingest being the first skill that reads
  `10-sources/`.

## R17. Code name and the description

- **Decision**: `status` returns `client_label`, as in 002 R7. `verify` searches the front
  matter and every section outside the content region of each source, plus the index rows
  and changelog lines the skill wrote, for the real client name, case-insensitively. It
  reports `real-name-leak` with the file and section only. The content region is excluded:
  it stays verbatim (FR-024).
- **Rationale**: Same mechanism as charter. The content can't be redacted, because it is
  evidence.

## R18. Testing strategy

- **Decision**: Three levels, as in 002 R20.
  1. **Automated (pytest, always run)**:
     - *Script unit tests*: each format parser, every transcript shape, merging caption
       cues, Word headings, lists, tables, merged cells, comments, tracked changes, charts
       and images. Also numbering, duplicates by hash, the policy gate (exit 3; restricted
       file `chmod 000`), `verify` (mismatch detection, corrected callouts, leaks),
       `finalize`, `set-status`, `restrict`, `refs`, and the byte-identity of `raw/` before
       and after every command (SC-001).
     - *PDF tests* run in both modes. Checked-mode tests need `pdftotext` and are skipped
       with a reason when it's missing. Unchecked-mode tests hide poppler by running the
       script with a `PATH` that leaves it out. They cover the header and encryption
       checks, the page-count estimate, the skeleton, the structural `verify` and the
       `fidelity-unchecked` warning.
     - *Fixtures are generated at test time* by `tests/fixtures/ingest/make_fixtures.py`:
       Word files with `zipfile`, and PDFs with a small built-in writer (a text page, a
       table page, a chart drawn with vector paths, an image-only "scanned" page, a page
       with roman-numeral page labels, and a 40-page document for resume tests). No binary fixtures are committed, and all the text is
       synthetic.
     - *Asset tests*: the skill ships with valid front matter. `init` and `refresh` deliver
       it. The template has the new fields. The change-convention copies are identical.
       The parser parity with `charter.py` holds.
  2. **Skill evaluation (opt-in, `CAIRN_SKILL_EVAL=1`)**: scenarios for US1–US4 and the
     main edge cases, extending `tests/skill_eval/` to load scenarios per skill. Policy
     scenarios plant a canary in a restricted file and assert that it appears nowhere in the
     transcript or the files (SC-002). One scenario runs with poppler hidden from `PATH`.
     The harness then measures how well the assistant copies text by comparing sampled
     pages against `pdftotext` itself. Every scenario asserts that `raw/` is
     byte-identical before and after, and that `verify` passes on every source written.
  3. **Manual**: the quickstart walkthrough, and the Phase 1 trial engagement held locally
     for SC-006 and SC-007. It is never committed.

## R19. Skill front matter

- **Decision**:

  ~~~yaml
  name: ingest
  description: "Turn client documents, meeting transcripts and meeting notes in 10-sources/raw/ (PDF, Word, markdown, text, VTT, SRT) into cited, verbatim source files, respecting the engagement's model-use policy. Use when new material arrives, or to review and approve extracted sources."
  argument-hint: "[file(s) in 10-sources/raw/, or 'review' …] [context: who provided it, when, why it matters]"
  allowed-tools: Read, Edit, Write, Bash(python3 *ingest.py*)
  ~~~
  The `*ingest.py*` pattern follows 002 R21, and `cairn init` and `refresh` add the
  matching rule to `.claude/settings.json`.

## R20. Framework version

- **Decision**: Bump `cairn.__version__` from `0.2.0` to `0.3.0`. The changes add a skill
  and change the source template and the change convention. `refresh` brings both to
  existing engagements. The changelog seed's guidance change applies to new engagements
  only. The convention's full text reaches existing engagements through the refreshed
  skills.
