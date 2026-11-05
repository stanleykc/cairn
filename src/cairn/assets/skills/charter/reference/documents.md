# Using a document

Use this whenever the consultant names a document (a SOW, brief, proposal or change
order) or pastes document text, up front or at any point in the session. Drafting from
what you read is in `reference/interview.md` ("Drafting from a document"); revision mode is
in `reference/review-and-revise.md` ("Revising from a document").

## 1. A named file: always gate it with `doc`

1. Run `charter.py doc "<what the consultant named>"`, on its own, before anything else
   touches the file. Pass the name or path exactly as given; the helper resolves it.
2. **Exit 4 (refused).** Nothing was read. Tell the consultant `detail` (what happened and
   why) and `next_step` (what to do instead), in your own short words, keeping every
   instruction in `next_step` (for example the `cp` command). Then use the table below for
   anything else to say, and carry on with the plain interview.
   - `needs-permission`: show `model_use_notes` and ask **"May I use <document> under
     these restrictions?"**. Rerun `doc` with `--permitted` only after an explicit yes in
     this session. On a no, ask for a summary in their own words that leaves out what the
     restrictions cover.
3. **Exit 0 (cleared).** Read it:
   - `read_with: "Read"` (PDF, markdown, text): `Read` the returned `path`, exactly as
     returned. Read PDFs 20 pages at a time, and stop once every interview topic is covered
     or the document ends.
   - `read_with: "text"` (`.docx`): use `text`; don't `Read` the file.
   - If the output has `next_step` (the text was cut short), tell the consultant now.
4. Then list the topics it covers and doesn't, and draft (`reference/interview.md`).

Never `Read` a document `doc` did not clear, never at a path other than the one it
returned, and never list or search `10-sources/` (not even to find a file name or check it
exists). Never open `10-sources/extracted/`.

## 2. Pasted document text: apply the policy yourself

Text pasted into the conversation can't be gated by the helper; it has already reached
you. Your only control is whether you use it and record it:

- `allowed`: use it.
- `restricted`: show the recorded restrictions and ask "May I use this text under these
  restrictions?" Use it only on an explicit yes.
- `unconfirmed`: don't use it. Write nothing drawn from it, and say so (G9).

If the consultant didn't say what the text is, ask for a few words (for example "SOW
section 3") before drafting; that description names it in provenance:
`pasted text (<their description>)`.

## 3. When a document can't be used

Every message says **what happened, why, and what to do instead**. Never say only "I
can't use this", and always offer to carry on with the plain interview.

| # | Case | What to tell the consultant |
|---|---|---|
| G1 | `policy-unconfirmed` | The model-use policy isn't settled, so I can't read client documents yet. Settle it now: allowed, restricted (and what can't be sent), or still unconfirmed. If you can't yet, we'll carry on with the plain interview and you can summarize the document in your own words. |
| G2 | `outside-raw` | I only read documents inside this engagement's `10-sources/raw/`. Copy it there: from the engagement folder, run `cp "<their path>" 10-sources/raw/` (originals there are never changed), then name it again. Or paste the relevant sections, if the policy permits it. |
| G3 | `not-found` | I couldn't find that name in `10-sources/raw/`. Check the file name, including its extension, and that it was copied there. I don't list that folder, so I need the exact name. |
| G4 | `unsupported-format` (`.doc`, `.pages`, `.pptx`, `.xlsx`, images…) | I can read PDF, .docx, .md and .txt only. Save or export it as one of those, copy it into `10-sources/raw/` and name it again; or paste the relevant text. |
| G5 | `restricted-source` | `ingest` registered this file as restricted, so it may not be sent to the model. Summarize the relevant points in your own words. If the restriction was recorded by mistake, correct it through `ingest`, not `charter`. |
| G6 | `needs-permission` | Show the restrictions and ask "May I use <document> under these restrictions?". On no: summarize in your own words, leaving out what the restrictions cover. |
| G7 | Cleared but unreadable: `unreadable`, or `Read` returns no text (scanned, password-protected, empty) or fails | No text could be read from it (say which, if you can tell). Save an unlocked or text copy (export to .docx or .txt, or run OCR) into `10-sources/raw/` and name it again; or paste the relevant sections. |
| G8 | `truncated: true`, or a long PDF where some topics weren't in the pages read | Only part of it was read. Paste the sections that cover the missing topics, or put a shorter extract in `10-sources/raw/`. |
| G9 | Pasted text under `unconfirmed` | I haven't used the text you pasted, and nothing was written from it, because the model-use policy isn't settled. Settle it now, or summarize in your own words. |
| G10 | Pasted text under `restricted` | As G6: "May I use this text under these restrictions?"; on no, ask for a summary instead. |
| G11 | Pasted text with no description | Ask for a few words on what it is (for example "SOW section 3"); use them to name it in provenance. |
| G12 | The document covers none of the interview topics | Say so, briefly; run the usual interview. |
| G13 | Documents conflict, or the consultant contradicts a document | Show both versions once and ask which to keep. The consultant's answer wins. |
| G14 | The document names the real client while a code name is in use | Say once that you'll write `<client_label>` instead. Never write the real name. |
| G15 | Revision mode: no differences from the charter | Say no changes were found; write nothing. |
