# Quickstart: Validating the Ingest Skill

Runnable checks that show `ingest` works end to end. Formats and rules are in
[data-model.md](data-model.md) and [contracts/](contracts/). Every file used here is
synthetic (Principle VIII).

## 0. Prerequisites

- The `cairn` repo with dev dependencies: `python3 -m pip install -e '.[dev]'`
- poppler on PATH, recommended: `brew install poppler` (macOS) or `apt install
  poppler-utils`. Check with `pdftotext -v`. The skill works without it (§6a), but
  checked-mode PDF tests need it.
- For §3–§7: Claude Code (`claude` CLI), signed in.

## 1. Automated tests

```bash
python3 -m pytest tests/unit/test_ingest_script.py tests/integration/test_ingest_bundle.py \
    tests/integration/test_ingest_golden.py -q
```

Expected: all pass. PDF tests are skipped, with a reason, only if `pdftotext` is missing.
The suite includes:

- byte-identity of `raw/` around every command (SC-001);
- the policy gate (exit 3, with the restricted original made unreadable by `chmod 000`)
  (SC-002);
- the field checks (SC-003), word-for-word fidelity (SC-004) and tables and locators
  (SC-005).

## 2. Build a synthetic engagement

```bash
cd "$(mktemp -d)"
python3 -m cairn init --no-git --engagement "Fulfillment Review" --code-name Northwind \
    --lead "Test Lead" --start-date 2026-11-03
cd fulfillment-review*
python3 /path/to/cairn/tests/fixtures/ingest/make_fixtures.py 10-sources/raw/
shasum -a 256 10-sources/raw/* > /tmp/raw-before.sha
```

`make_fixtures.py` writes the synthetic test set:
- PDFs: a text PDF with a table and a chart, a scanned PDF, a PDF with a hard page, and
  a 40-page PDF;
- a Word document with headings, a table, an image, a chart, a comment and a tracked
  change;
- a markdown transcript and the same meeting as `.vtt`;
- a meeting summary and a markdown client document;
- a plain-text note, a `.pptx` stub, and a duplicate copy of one PDF.

## 3. Policy `unconfirmed` (US3-1)

Leave `model_use: unconfirmed`. Run `claude`, then `/ingest`.

Expected: the skill says to settle the policy with `/charter`, and stops. Then check:
- `git status` (or a diff of the folder) shows nothing written;
- `python3 .claude/skills/ingest/scripts/ingest.py extract kickoff.vtt` exits 3.

## 4. Policy `restricted`, with a canary (US3-2–4, SC-002)

Set the policy with `/charter`: restricted, "no HR files". Put a file
`10-sources/raw/hr-attrition.md` containing `CANARY-ingest-91c2`. Run `/ingest` and,
when asked, say that `hr-attrition.md` may not be sent and everything else may.

Expected:
- `hr-attrition.md` has an `S-###` with `restricted: true` and `extraction_method: none`,
  and its index row shows `yes`.
- `grep -r CANARY-ingest-91c2 --exclude-dir=raw .` finds nothing.
- The session transcript (`~/.claude/projects/…/*.jsonl` for this session) has no
  match for the canary.

## 5. Full ingest (US1, US2)

Run `/ingest` with no arguments. Give one line of context per file. Name the generic
speakers when asked.

Expected:
- One `S-###` per supported file. Skipped: the `.pptx` (not supported yet) and the duplicate
  PDF (identical to an existing `S-###`).
- `python3 .claude/skills/ingest/scripts/ingest.py verify` → exit 0.
- The text PDF has `### p. n` markers and its table as a markdown table. Its chart has a
  `[!derived] vision-description` callout.
- The scanned PDF has `[!derived] ocr`, `extraction_method: ocr` and `derived: true`.
- The hard page is listed in `uncertain_passages`.
- The Word source keeps its headings, its table as a markdown table, its chart as a
  `chart-data` callout with a description, its comment under `cairn:comments`, and its
  tracked change inline and listed as uncertain.
- Both transcripts have one turn per speaker change, with `[T# · hh:mm:ss]`, and the same
  words. Confirmed names appear in `## Speakers` only.
- The summary has `material: meeting-notes`, `author`, `author_kind`, `meeting_date`,
  `attendees` and `origin: interview-meeting`.
- The plain-text note has `[¶n]` markers.
- Titles, descriptions and index rows say "Northwind", never the real name.
- Every source is `proposed` and `internal`.
- `shasum -a 256 -c /tmp/raw-before.sha` reports every file OK (SC-001).

## 6. Interrupt and resume (edge case)

Start `/ingest` on the 40-page fixture PDF, and stop the session after the first batch of
pages.

Expected: `status` shows the source as `in-progress` with `pages_reviewed: 20`, and it has
no index row. Running `/ingest` again resumes at page 21 and finishes with one index row.

## 6a. PDFs without poppler (R4)

Start Claude Code with poppler hidden from `PATH`:
`PATH=$(echo "$PATH" | tr ':' '\n' | grep -v homebrew | paste -sd: -) claude`. Adjust
the filter to wherever poppler is installed. Then ingest the text PDF fixture.

Expected:
- `status` reports `pdf_backend.mode: unchecked`, and the session mentions the install
  hint once, without stopping.
- The source has `### p. n` markers for every page, `fidelity: unchecked`, and the same
  table and chart callouts as in §5.
- `verify` exits 0, with a `fidelity-unchecked` warning.
- The end summary lists the source under "To spot-check" with sample pages, and
  `/ingest review` shows it first, with page text next to page images.
- Compare the copied text with `pdftotext` (poppler restored). The sampled pages should
  match word for word. Any differences show how far an unchecked copy can be trusted.

## 7. Review and correct (US4)

Run `/ingest review`. Then:
- approve one source;
- reject one, giving a reason and trigger;
- correct the planted OCR error on the scanned PDF;
- give no instruction for the rest.

Expected:
- The approved source is `active` in both its file and the index.
- The rejected one is `rejected`, with `change_reason` set and a `reject` line in the log.
- The fix appears as a `[!corrected]` callout with `was:`, is removed from the uncertain
  list, and is logged with an `extraction-fix · -` line holding the previous text.
- `verify` still passes.
- Observations citing the source are listed. Put a synthetic `30-observations/O-001.md`
  with `source: "S-00x"` there first.
- The other sources are unchanged and still `proposed`.

## 8. Skill evaluation (opt-in)

```bash
CAIRN_SKILL_EVAL=1 python3 -m pytest tests/skill_eval -k ingest -q
```

Expected: every ingest scenario passes. Scenarios cover US1–US4 plus these edge cases:
- a duplicate file;
- an unsupported format;
- a file outside `raw/`;
- a new version of a source;
- an AI note-taker summary (confidence capped at medium);
- an instruction planted inside a source (it isn't followed);
- restricting a source after ingest.

## 9. Trial engagement (manual, local only)

Run the full flow on the anonymized Phase 1 trial engagement, held locally and never
committed. Record:
- hands-on minutes for a batch of 10 sources (SC-006, target < 20);
- the share of sources the lead consultant judges usable without correction (SC-007,
  target ≥ 90%).
