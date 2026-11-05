# Contract: `charter.py doc`

Extends `specs/002-charter-skill/contracts/charter-script.md`. Script version 0.2.0 →
0.3.0. Standard library only, no network, and it never writes a file.

```text
python3 charter.py [--root PATH] doc RAW [--permitted]
```

- `RAW`: the file the consultant named, either relative to `10-sources/raw/` or as a path
  that resolves inside it.
- `--permitted`: the consultant confirmed in this session that this document may be used
  under the `restricted` policy. It has no effect under `allowed`, and it is ignored
  under `unconfirmed`.

## Checks, in order

1. The engagement is found, otherwise exit 2 (as for every command).
2. Policy `unconfirmed` → refuse `policy-unconfirmed`.
3. Resolved path (with symlinks followed) not inside `10-sources/raw/` → refuse
   `outside-raw`.
4. Not an existing regular file → refuse `not-found`.
5. Extension not `.pdf`, `.docx`, `.md`, `.markdown` or `.txt` → refuse
   `unsupported-format`.
6. An `10-sources/extracted/S-*.md` has `restricted: true` and `raw_file` equal to this
   file → refuse `restricted-source` (with `restricted_source: S-###`).
7. Policy `restricted` without `--permitted` → refuse `needs-permission`.

The checks run in this order, so policy problems are reported before path problems. The
file itself is opened only after every check passes, and only for `.docx`.

## Output (JSON on stdout)

Exit 0 (readable):

```json
{
  "document": "sow-2026-10.pdf",
  "path": "/abs/path/to/engagement/10-sources/raw/sow-2026-10.pdf",
  "format": "pdf",
  "read_with": "Read",
  "model_use": "allowed",
  "text": null,
  "truncated": false
}
```

For `.docx`: `"read_with": "text"`. `text` holds the document text: paragraphs in order,
headings as `#` lines, table rows as `| a | b |` lines. It is capped at 200,000
characters (`truncated: true` when capped) and redacted for the code name (R7).

Exit 4 (refused). Nothing was opened:

```json
{
  "refused": "needs-permission",
  "document": "sow-2026-10.pdf",
  "model_use": "restricted",
  "model_use_notes": "No pricing or personal data to external AI",
  "detail": "Ask the consultant whether this document may be used under the restrictions, then rerun with --permitted."
}
```

| `refused` | Skill's next step |
|---|---|
| `policy-unconfirmed` | Explain; offer to settle the policy (Step 2), else continue with the plain interview |
| `outside-raw` | Ask the consultant to copy the file into `10-sources/raw/`, or paste the relevant text |
| `not-found`, `unsupported-format` | Say so; continue with the plain interview |
| `restricted-source` | Explain that ingest registered it as restricted; ask for a summary instead |
| `needs-permission` | Show `model_use_notes`, ask the consultant; rerun with `--permitted` only on a yes |

Exit 3: usage error (as for other commands). Exit 4 is new and used only by `doc`.

## Invariants

- No file is written, moved or renamed (Principle II).
- Under `10-sources/`, the only things read are the named file (`.docx` only) and the
  `restricted` and `raw_file` front-matter fields of `10-sources/extracted/S-*.md`.
- The real client name never appears in output when a code name is in use.
- `status`, `check`, `refs` and `model-use` are unchanged.
