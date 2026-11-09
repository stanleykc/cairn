# Contract delta: observation file

Amends `specs/005-extract-observations/contracts/observation-file.md`.

## Invariants (changed and added)

5. `questions` holds at least one ID, and every ID was `active` or `proposed` when the file
   was written. Link fields are empty.
9. (new) `relevance` is one line, at most 240 characters, and names every ID that was in
   `questions` when the file was written. It doesn't restate the claim. A later `tag` may add
   a question that `relevance` doesn't name; the changelog records why.
10. (new) Observations written before 006 may lack `relevance` and may have
    `questions: []`. They stay valid for `verify`.

## Example front matter (excerpt)

```yaml
source: "S-001"
locator: "T42"
questions: ["Q-001"]
relevance: "Q-001: names a manual re-keying step between the order portal and invoicing"
derived: false
speaker: "Dana Reyes"
```
