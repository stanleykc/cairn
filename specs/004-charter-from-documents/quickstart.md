# Quickstart: validating charter-from-documents

All documents are synthetic (Principle VIII).

## Prerequisites

- `python3 -m pip install -e '.[dev]'`
- For live evals: the `claude` CLI on PATH and `CAIRN_SKILL_EVAL=1`

## 1. Deterministic checks (no model)

```bash
python3 -m pytest tests/unit/test_charter_script.py -k doc
python3 -m pytest tests/unit tests/integration
```

Expected:

- `doc` exits 4 with `policy-unconfirmed`, `outside-raw`, `not-found`,
  `unsupported-format`, `restricted-source` and `needs-permission` in the matching
  fixtures, and exits 0 for `allowed` and for `restricted --permitted`
  (contracts/charter-doc-command.md).
- A `.docx` SOW fixture returns its headings, paragraphs and table rows; a code-name
  fixture returns no real client name.
- No file under the engagement changes after any `doc` call.
- All existing charter tests still pass (SC-006).

## 2. Manual walk-through

```bash
cairn init demo-eng            # follow the prompts; leave model use unconfirmed
cp tests/fixtures/charter/documents/sow-synthetic.pdf demo-eng/10-sources/raw/
cd demo-eng && claude
```

1. `/charter use the SOW in 10-sources/raw/sow-synthetic.pdf`. Expected: asked for the
   policy first; the document isn't read.
2. Answer "allowed". Expected: the skill lists the covered topics (objectives,
   boundaries, deliverables, timeline, stakeholders) and the uncovered ones.
3. Confirm objectives, correct one deliverable date, and skip constraints. Expected:
   `scope.md` holds the corrected date; skipped topics are listed under `Not covered`.
4. Expected end summary: `From documents: sow-synthetic.pdf → …`, plus a matching
   changelog line. Any Q/H/A from the SOW is `consultant-note` with "From
   sow-synthetic.pdf, confirmed by the consultant".
5. Ask it to read `~/Downloads/sow.pdf`. Expected: refused (`outside-raw`), with a
   suggestion to copy the file into `raw/` or paste the text.

## 3. Live evals (opt-in)

```bash
CAIRN_SKILL_EVAL=1 python3 -m pytest tests/skill_eval -k charter
```

Expected: the new and updated scenarios pass (research R10). The canary text is read only
in scenarios that list the document under `documents_allowed`, and is never read under
`unconfirmed` (SC-003).
