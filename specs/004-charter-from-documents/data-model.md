# Data Model: Charter From Engagement Documents

There are no new object types, files or front-matter fields. The charter's files and
templates (002 `data-model.md`) are unchanged. This feature adds one transient entity
and changes how three existing fields and the changelog are filled.

## Engagement document (transient, never stored by `charter`)

| Attribute | Values | Notes |
|---|---|---|
| kind | `file` \| `pasted` | |
| name | file path relative to `10-sources/raw/`, or "pasted text (<consultant's description>)" | Used in confidence reasons, the changelog and the end summary |
| format | `pdf` \| `docx` \| `md` \| `txt` | `file` only. Same set `ingest` reads (`.markdown` counts as `md`) |
| permission | `allowed` \| `permitted-in-session` \| `refused` | From the policy (R4). `refused` documents are never read |

Validation:

- A `file` must resolve, after following symlinks, to a regular file inside
  `10-sources/raw/` (FR-001).
- A `file` registered as restricted by `ingest` is always `refused` (R3).
- When the policy is `unconfirmed`, every document is `refused`, whatever was confirmed
  (FR-004, FR-005).

State per document, within one session:

```text
named ──doc refuses (unconfirmed / outside-raw / restricted-source / unsupported / not-found)──▶ refused
named ──doc: needs-permission──▶ awaiting consultant ──"yes"──▶ doc --permitted ──▶ readable
                                                     └─"no"───▶ refused (ask for a summary)
named ──doc exit 0 (allowed)──▶ readable ──▶ drafted answers per topic ──confirm/correct/skip──▶ written | skipped
```

## Drafted answer (transient)

One per interview topic the document covers: the topic number (1 to 10 in
`reference/interview.md`), the drafted text, and the document name. It is shown to the
consultant and written only once confirmed or corrected (FR-009). It is never written to
disk as a draft.

## Changes to existing fields

| Where | Field | Rule |
|---|---|---|
| `questions.md`, `hypotheses.md`, `assumptions.md` | `origin` | Still `consultant-note` for document-drawn items (Clarification Q2). `llm-inference` for kept suggestions, unchanged |
| same | `confidence_reason` | For a document-drawn item confirmed as drafted or lightly edited: starts with `From <document name>, confirmed by the consultant`. For an item the consultant rewrote: as for any answer (FR-013) |
| same | `status`, `audience` | Unchanged: `proposed`, `internal` (FR-011) |
| same | source citations | None. Never an `S-###`, never `client-document` (002 FR-019 holds) |
| `60-log/changelog.md` | new line type | One line per document used in a session: `<date> · charter · drew <topics> from <document name> (consultant confirmed)` |
| End summary | new line | `From documents: <name> → <topics>; …` (omitted when no document was used) |
