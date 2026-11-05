# Charter fixtures

Synthetic engagements used by the `charter.py` unit tests, the golden tests
(`tests/integration/test_charter_golden.py`) and the opt-in skill evaluation
(`tests/skill_eval/`).

| Fixture | What it holds |
|---|---|
| `empty/` | A freshly initialized engagement at framework 0.2.0: seed charter files, no items |
| `drafted/` | A drafted charter: scope filled, `Q-001`–`Q-003`, `H-001`–`H-002`, `A-001`, stakeholders and lenses, all `proposed`; model use `restricted` |
| `approved/` | An approved charter: `Q-001`–`Q-004`, `H-001`–`H-003`, `A-001`–`A-002`, all `active`, plus one observation and one finding that link to charter items |
| `revised/` | `approved/` after a revision: a new question, a superseded hypothesis, a rejected assumption, a pending revision and a changed timeline |
| `broken/` | `drafted/` with deliberate defects; `check` must report the expected problem codes |
| `codename/` | An engagement that uses the code name "Northwind" for the client "Globex" |
| `documents/` | Synthetic engagement documents (feature 004): a SOW as `.md`, `.pdf` and `.docx`, a SOW naming "Globex" (`.md`, `.docx`), a change order against `approved/`, a scanned PDF, an encrypted PDF and a legacy `.doc`. Regenerate with `python3 tests/fixtures/charter/documents/make_documents.py` |

Rules:

- **Synthetic names only** (constitution Principle VIII): "Acme", "Globex", the code name
  "Northwind", and the lead "Test Lead". Never use a real client, person or engagement.
- **Never modify a fixture in place.** Tests copy a fixture to `tmp_path` first, then run
  `charter.py` (or edit files) against the copy.
- **`10-sources/` canaries are created at test time**, never committed. Tests that check
  the script never opens `10-sources/` create an unreadable canary file there in the copy.
- **Documents are copied into a test copy's `10-sources/raw/` at test time**, never
  committed under a fixture's `10-sources/`.
- Empty canonical folders are not committed (git cannot hold them). Tests that need them
  create them in the copy.
