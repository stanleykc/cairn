# Contract: changes to the `charter` skill instructions

Amends `specs/002-charter-skill/contracts/charter-skill.md`. Only the differences are
listed. Everything else in the 002 contract stands.

## Front matter

- `description`: replace "Never reads client documents." with "Can draft answers from a
  SOW, brief or change order in 10-sources/raw/ (or pasted), once the model-use policy
  allows it."
- `argument-hint`: add "[a document in 10-sources/raw/ to draft from]".
- `allowed-tools`: unchanged (`Read` is already allowed; `doc` runs through the existing
  `Bash(python3 *charter.py*)` rule).

## Never list

| # | 002 rule | New rule |
|---|---|---|
| 1 | Never open, list, search or read anything in `10-sources/`, or any document the consultant offers | Never list or search `10-sources/`. Never Read any file there, or anywhere else, except a document the consultant named and `charter.py doc` cleared (exit 0), at the path it returned. Never use pasted document text unless the policy permits it (Step 2) |
| 6 | Never cite a source ID or write `origin: client-document` | Unchanged. Document-drawn items are `consultant-note` |
| new 10 | — | Never write anything drawn from a document without the consultant confirming that topic |

## Step 2: Model use and documents

- Item 2 reminder text: "Please don't paste text from client documents until the
  model-use policy allows it. Summarize in your own words instead."
- Item 3 is replaced by "Using a document":
  1. When the consultant names a document (up front or at any point), run `doc RAW`.
  2. On exit 4, follow the refusal table in `contracts/charter-doc-command.md`. On
     `needs-permission`, show the notes and ask: "May I use <document> under these
     restrictions?" Rerun with `--permitted` only on an explicit yes.
  3. On exit 0, read it (`Read` the returned path, or use `text` for `.docx`). Then list
     the interview topics it covers and those it doesn't (FR-008).
  4. For pasted document text, apply the same policy decision without the script:
     `allowed` → use it; `restricted` → ask as in 2; `unconfirmed` → don't use it, and
     ask for a summary.

## Step 4: Interview (and `reference/interview.md`)

"Anything given up front" also covers a document. For a covered topic, show the drafted
answer, in the document's wording where practical, and ask the consultant to confirm,
correct or skip it. Topics the document doesn't cover get the usual prompt. If the
consultant contradicts the document, their answer wins; point out the conflict once.
Hunches in the document are offered as candidate hypotheses or assumptions, never as
facts.

## Step 5: Revision mode (and `reference/review-and-revise.md`)

With a document: list only its differences from the current charter, and propose each
change under the change convention with trigger "new document: <name>".

## Writing rules (and `reference/formats.md`)

- `confidence_reason` for document-drawn Q/H/A: `From <document>, confirmed by the
  consultant` (see data-model.md).
- After saving topics drawn from a document, append one changelog line per document (see
  data-model.md).

## Step 8: End summary

Add, after `Changed:`:

```text
From documents: sow-2026-10.pdf → Objectives, Boundaries, Deliverables, Timeline, Stakeholders
```

Leave the line out when no document was used. Change the `Next:` hint "add originals to
10-sources/raw/ · run ingest" so that it is still suggested when the document used is not
yet ingested.
