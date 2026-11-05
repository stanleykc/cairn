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

8. A cleared `.docx` that is not a readable Word file (damaged, password-protected, not
   a zip) or holds no text → refuse `unreadable`. This is the only refusal raised after
   the file is opened.

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
characters (`truncated: true` when capped) and redacted for the code name (R7). When
`truncated` is true, the output also carries `next_step` (G8):

```json
{"document": "long.docx", "...": "...", "truncated": true,
 "next_step": "Only the first 200,000 characters were returned. If a topic you need is not in them, paste the sections that cover it, or put a shorter extract in 10-sources/raw/ and name it again."}
```

Exit 4 (refused). Nothing was opened (except for `unreadable`). Every refusal carries
`detail` (what happened and why) and `next_step` (consultant-facing: exactly what to do
instead):

```json
{
  "refused": "needs-permission",
  "document": "sow-2026-10.pdf",
  "model_use": "restricted",
  "model_use_notes": "No pricing or personal data to external AI",
  "detail": "The model-use policy is restricted (No pricing or personal data to external AI). Ask the consultant whether this document may be used under these restrictions, then rerun with --permitted.",
  "next_step": "Say whether sow-2026-10.pdf may be used under these restrictions. If yes, it will be read. If no, summarize the relevant points in your own words, leaving out what the restrictions cover."
}
```

`refused_source` fields: `restricted-source` adds `restricted_source: "S-###"`;
`needs-permission` adds `model_use_notes`. `<path>` below is the path exactly as given;
`<name>` is the file name relative to `10-sources/raw/` (or the given path when it is
outside).

| `refused` | Guidance | `detail` (why) | `next_step` (what to do instead) | Skill's next step |
|---|---|---|---|---|
| `policy-unconfirmed` | G1 | The model-use policy is unconfirmed, so no client document may be sent to the model yet. Nothing was opened. | Settle the model-use policy now: allowed, restricted (say what can't be sent), or still unconfirmed. If you can't settle it yet, carry on with the plain interview and summarize the document in your own words. | Explain; offer to settle the policy (Step 2), else continue with the plain interview |
| `outside-raw` | G2 | `<path>` is not inside this engagement's 10-sources/raw/. charter only reads documents kept there. Nothing was opened. | Copy it into the engagement: from the engagement folder, run `cp "<path>" 10-sources/raw/` (originals there are never changed), then name it again. Or paste the relevant sections, if the model-use policy permits it. | Show the copy command; continue with the plain interview meanwhile |
| `not-found` | G3 | No file named `<name>` was found in 10-sources/raw/. | Check the file name, including its extension, and that the file was copied into 10-sources/raw/. charter does not list that folder, so it needs the exact name. | Ask for the exact name; never list or search `10-sources/` |
| `unsupported-format` | G4 | `<name>` is a `.<ext>` file. charter reads only PDF, .docx, .md and .txt. Nothing was opened. | Save or export it as one of PDF, .docx, .md, .txt, copy that into 10-sources/raw/ and name it again. Or paste the relevant text. | Say so; continue with the plain interview |
| `restricted-source` | G5 | ingest registered `<name>` as restricted (`S-###`), so it may not be sent to the model. Nothing was opened. | Summarize the relevant points in your own words instead. If the restriction was recorded by mistake, correct it through ingest, not charter. | Ask for a summary in the consultant's own words |
| `needs-permission` | G6 | The model-use policy is restricted (`<notes>`). Ask the consultant whether this document may be used under these restrictions, then rerun with --permitted. | Say whether `<name>` may be used under these restrictions. If yes, it will be read. If no, summarize the relevant points in your own words, leaving out what the restrictions cover. | Show `model_use_notes`, ask "May I use <document> under these restrictions?"; rerun with `--permitted` only on a yes |
| `unreadable` | G7 | `<name>` could not be read as a Word document, or it holds no text (it may be damaged, password-protected or not really a .docx). | Save an unlocked or text copy (export to .docx or .txt) into 10-sources/raw/ and name it again. Or paste the relevant sections. | Say so; continue with the plain interview |

Exit 3: usage error (as for other commands). Exit 4 is new and used only by `doc`.

## Invariants

- No file is written, moved or renamed (Principle II).
- Under `10-sources/`, the only things read are the named file (`.docx` only) and the
  `restricted` and `raw_file` front-matter fields of `10-sources/extracted/S-*.md`
  (listing `10-sources/extracted/` to find them).
- `detail` and `next_step` never tell the consultant only "I can't use this": every
  `next_step` names a concrete alternative.
- The real client name never appears in output when a code name is in use.
- `status`, `check`, `refs` and `model-use` are unchanged.
