# Research: Charter From Engagement Documents

All Technical Context unknowns are resolved below. Each entry: Decision, Rationale,
Alternatives considered.

## R1. Where the policy gate lives

- **Decision**: Add a `doc` command to the charter helper (`charter.py doc RAW
  [--permitted]`). It decides whether a named document may be read, from the engagement
  record and the file's location only. The skill reads a document only after `doc` exits
  0, and only the path `doc` returns.
- **Rationale**: Constitution Principle I allows scripts where a deterministic check is
  more reliable than instructions. "Is the policy settled, is the file inside
  `10-sources/raw/`, is it registered as restricted" is exactly that kind of check, and
  `ingest` already gates originals the same way (`guard_original` in `ingest.py`). A
  script gate is also testable without a live model (SC-003).
- **Alternatives considered**: Instructions only (as the current refusal is). Rejected:
  the current problem shows that instruction-only rules are applied too broadly or too
  narrowly, and SC-003 should hold deterministically.

## R2. How each format is read

- **Decision**: PDF, markdown and plain text are read with the skill's existing `Read`
  tool, on the path `doc` returns (PDFs at most 20 pages per call). For `.docx`, `doc`
  itself prints the document's text: paragraphs in order, headings marked with `#`, table
  rows as `|`-separated lines. It uses only the standard library (`zipfile` plus
  `xml.etree`).
- **Rationale**: `Read` already handles PDF, markdown and text, and is already in the
  skill's `allowed-tools`, so the permission surface does not grow. `Read` can't read
  `.docx`, and charter needs only the readable text, not ingest's verbatim fidelity, so
  a short reader (about 40 lines) is enough.
- **Alternatives considered**: (a) Calling `ingest.py`: adds a cross-skill dependency
  and a second `Bash` permission, and ingest writes source files, which charter must not
  do. (b) Copying ingest's `DocxReader` (~480 lines): far more than charter needs.
  (c) Asking the consultant to save Word files as PDF: needless friction.

## R3. Checking for a registered restricted source

- **Decision**: `doc` refuses a file when any `10-sources/extracted/S-*.md` has
  `restricted: true` and a `raw_file` equal to the named file. It reads only those two
  front-matter fields and never prints anything else from `10-sources/extracted/`.
- **Rationale**: Once `ingest` has registered a file as restricted, no skill may send it
  to a model (Principle VIII). Without this check, charter could read a file that ingest
  refuses.
- **Alternatives considered**: Ignoring ingest's registrations. Rejected as a
  confidentiality gap. The helper's old invariant "never opens anything under
  `10-sources/`" is narrowed to: it opens only the named raw file (only for `.docx`) and
  the `restricted`/`raw_file` front matter of extracted sources. The 002 script contract
  and its unit test (R6 in 002) are updated to match.

## R4. Restricted policy: per-document permission

- **Decision**: Under `restricted`, `doc` without `--permitted` refuses with
  `needs-permission` and returns `model_use_notes`, so the skill can show the recorded
  restrictions. The skill passes `--permitted` only after the consultant confirms in
  this session that this document is allowed. Under `allowed`, `--permitted` is not
  needed. Under `unconfirmed`, `doc` always refuses, even with `--permitted`.
- **Rationale**: Matches spec FR-005 to FR-007 and ingest's behavior ("before the
  consultant has said a file may be sent under `restricted`"). The consultant judges the
  restriction; the script enforces that the question was asked.
- **Alternatives considered**: Having the script interpret the restriction notes.
  Rejected: free text, and judging it is the consultant's call.

## R5. Pasted document text

- **Decision**: Pasted text can't be gated by a script. The rule is in the skill
  instructions: the skill uses pasted document text only when the policy is `allowed`,
  or `restricted` with the consultant's confirmation for that text. Otherwise it writes
  nothing from the pasted text, says why, and asks for a summary in the consultant's own
  words. The one-time reminder under `restricted`/`unconfirmed` stays, reworded: "Please
  don't paste text from client documents until the model-use policy allows it."
- **Rationale**: Text pasted into the conversation has already reached the model, so the
  only control left is whether it is used and recorded. Keeping the reminder reduces the
  chance it is pasted at all.
- **Alternatives considered**: Always accepting pasted text. Rejected by FR-002 and
  FR-004.

## R6. Provenance for document-drawn items

- **Decision**: Questions, hypotheses and assumptions drawn from a document keep
  `origin: consultant-note`, and their `confidence_reason` starts with "From
  <document>, confirmed by the consultant". Here <document> is the file name, or "pasted
  text (<consultant's description>)". If the consultant rewrote the item in their own
  words, the reason is written as for any other answer. Scope sections, stakeholders and
  lenses have no per-item provenance field. For them, one changelog line per document
  used records which topics were drawn from it, and the end summary gains a `From
  documents:` line.
- **Rationale**: Clarification Q2 (option A): no new origin value, no source citation, no
  constitution amendment. The changelog already records how the charter changed, and it
  is durable, which the end summary is not.
- **Alternatives considered**: Adding "(from SOW)" to every scope bullet and table row.
  Rejected: it clutters the charter and changes `formats.md` for every topic.

## R7. Client name in document text

- **Decision**: `doc` passes the `.docx` text it prints through the existing `redact()`,
  so the real client name never appears in its output when a code name is in use. For
  formats read with `Read`, the skill's existing rule (never write the real name) applies.
- **Rationale**: Reuses the 002 output-redaction rule at no cost, keeping the helper's
  invariant that it never prints the real client name.
- **Alternatives considered**: Redacting nothing. Rejected: the helper's contract
  forbids printing the real name.

## R8. Long documents

- **Decision**: `doc` caps `.docx` text at 200,000 characters and sets `truncated: true`
  when it hits the cap. The skill reads long PDFs in 20-page steps and stops once every
  interview topic is covered or the document ends. The skill never quotes more than it
  needs for a drafted answer.
- **Rationale**: SOWs are typically 5 to 40 pages; the cap only guards against
  pathological files.

## R9. Revision mode with a document

- **Decision**: In revision mode, the skill compares the document with the `status`
  output and the charter files. It proposes only the differences, one at a time, and
  each follows `change-convention.md`, with the trigger "new document: <name>".
- **Rationale**: Reuses the existing change convention (spec FR-019) without new helper
  code.

## R10. Tests

- **Decision**:
  - Unit tests for `doc`: each refusal code, path escapes (`..`, absolute paths
    elsewhere, symlinks leaving `raw/`), the `.docx` reader, redaction, truncation, and
    that `doc` never writes a file.
  - Update the 002 "10-sources is never opened" unit test so that only `doc` may touch
    the named raw file.
  - Live evals (opt-in, `CAIRN_SKILL_EVAL=1`): rewrite `us2-policy-allowed` (it now reads
    the brief) and `us2-policy-restricted`, and keep `us2-policy-unconfirmed` (it still
    refuses). Add scenarios for a pasted SOW, restricted-with-permission, a `.docx` SOW,
    a file outside `raw/`, and a change order in revision mode.
  - The charter eval assertion "no tool call names `10-sources/`" becomes per-scenario
    (`documents_allowed: [names]`).
- **Rationale**: SC-003 and SC-005 are checked deterministically where possible; the
  model's judgment is checked by the opt-in evals, as in 002 and 003.
