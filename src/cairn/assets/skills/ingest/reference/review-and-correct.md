# Review and correct

How to run `/ingest review`: spot-check extracted sources with the consultant, then approve,
reject, fix or restrict them, only on the consultant's explicit instruction. The changelog
format is in `change-convention.md`.

## 1. Gather

Run `status` and pick the sources to review: the IDs the consultant named, or every
complete source that is still `proposed`. Then run `review <IDs>`. It returns, per source,
locators and line numbers only, never text:

- `derived`: OCR, vision descriptions, chart data, diagram text (locator, kind, line);
- `tables`: locator, rows, columns, line, `built_by` (`assistant` for PDF tables you
  rebuilt, `script` otherwise);
- `uncertain`: locator and line;
- `corrected`, `comments`, `tracked_changes`, `fidelity`;
- `sample_pages` for unchecked PDFs.

Restricted sources come back as `restricted: true` only. Don't read them.

## 2. Show

Go through the sources in the order `review` gives them (unchecked PDFs first).

- **Unchecked PDF** (`fidelity: unchecked`): for each sample page, show the page's text
  from the source next to the page itself (Read the original with `pages` when poppler is
  installed, or the whole PDF when it is short). Ask the consultant to compare them word
  for word.
- **Every source**: show each derived passage, each table and each uncertain passage. Use
  Read with `offset` and `limit` at the line `review` gives, a few lines around it, rather
  than the whole file. Say which are derived (not verbatim) and why each uncertain passage
  is listed.

Keep it short: one source at a time, a numbered list of passages, then ask what to do.

## 3. Act, only on explicit instructions

| The consultant says | You do |
|---|---|
| approve | `set-status <ID> active`. If the source has `supersedes`, the old source becomes `superseded` and a `supersede` line is logged; list the `refs` the script returns. |
| reject | Ask for a reason (one line) and a trigger (`new-evidence`, `client-feedback`, `rethinking`) if either is missing; never invent one. Then `set-status <ID> rejected --reason "…" --trigger …`. List the `refs` it returns. |
| fix a passage | See §4. |
| mark restricted | See §5. |
| nothing for a source | Leave it `proposed` (SC-008). |

Approving never changes `audience`, and nothing ever sets `client-ready`.

## 4. Fix a passage (extraction fix)

Use this when the extraction misread the original (an OCR error, a wrong cell in a table
you rebuilt, a wrong word in a description). Never use it to change what the original says.

1. Replace the **whole passage** (the paragraph, the turn, the table row or the callout
   line) with a corrected callout:

   ```markdown
   > [!corrected] 2026-11-07
   > was: Figures are taken from the VMS shipment log, excluding returns.
   > Figures are taken from the WMS shipment log, excluding returns.
   ```

   The `was:` line holds the previous text exactly; the lines after it hold the new text.
   When the passage was inside a `[!derived]` callout, the header is
   `> [!corrected] 2026-11-07 · derived` and the source stays `derived: true`.
2. If the passage was listed as uncertain, remove it from `uncertain_passages` and from
   `## Uncertain passages`.
3. Append to `60-log/changelog.md` (the first event replaces "No changes yet."):

   ```text
   2026-11-07 · S-003 @ p. 3 · extraction-fix · OCR misread WMS · -
   > Figures are taken from the VMS shipment log, excluding returns.
   ```

   The detail line (the previous text) is required. Write ` · ` inside the reason as ` - `.
4. Run `verify <ID>`. It compares the `was:` text with the original, so the check still
   holds; `fix-unlogged` means step 3 is missing.
5. Run `refs <ID>` and list the observations or findings that cite this source by ID, so
   the consultant can check whether any relied on the misread passage.

## 5. Restrict a source after ingest

When the consultant says a source should not have been sent (or must not be used):

1. `restrict <ID> --reason "…"`. The script sets `restricted: true`, updates the index row
   and logs `restrict`.
2. Warn that the content was already processed in an earlier session and is still in the
   file; later skills will not read it.
3. Remove the content only when the consultant explicitly asks for it:
   `restrict <ID> --reason "…" --remove-content --by "<their name>"`. The script replaces the
   content with the restricted notice, clears `## Speakers` and `## Uncertain passages`,
   sets `content_removed: true` and `extraction_method: none`, and logs `remove-content`.
   This is the only deletion `ingest` ever makes.
4. List the `refs` the script returns.

## 6. A new version of a source

When `extract` returns `version_candidates` (the file name matches an existing source once
`v2`, `final`, dates and similar are stripped), ask whether the new file replaces that
source. Only on yes:

- set `supersedes: ["S-old"]` on the new source;
- ask for the reason and trigger now, and record them as `change_reason` and
  `change_trigger` on the new source.

The old source is untouched until the new one is approved; `set-status <new> active` then
supersedes it and logs the event.

## 7. Summary

End with the summary block from SKILL.md: what was approved, rejected, fixed or restricted,
and what is still `proposed`.
