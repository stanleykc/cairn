---
type: changelog
---

# Changelog

A dated record of every change to the engagement's ideas: supersede, correct, clarify,
reject, relink and scope change, plus model-use and charter approval, fixes to and
restrictions of sources, and question tags added to observations. Nothing is deleted; a
changed idea is recorded here instead. The full convention is in
`.claude/skills/charter/reference/change-convention.md` (the same text is in
`.claude/skills/ingest/reference/change-convention.md` and
`.claude/skills/extract-observations/reference/change-convention.md`).

Add one line per event, newest last:

`YYYY-MM-DD · <subject> · <event> · <reason> · <trigger>`

- subject: an ID (`A-###`, `O-###`), a new version (`<old ID> → <new ID>`), a moved link
  (`<H-ID>: <old Q-ID> → <new Q-ID>`), a source passage (`S-### @ <locator>`), a scope
  section (`scope/Timeline`), `charter` or `model-use`
- event: `supersede · correct · clarify · reject · relink · scope-change · model-use · approve-charter · extraction-fix · restrict · remove-content · tag`
- trigger: `new evidence · client feedback · rethinking · -` (`-` only for `model-use`,
  `approve-charter`, `extraction-fix`, `restrict`, `remove-content` and `tag`)

Previous text, or what moved or was wrong, goes underneath in lines starting with `> `.
It is required for `clarify`, `scope-change`, `correct`, `extraction-fix` and
`remove-content`. A literal ` · ` inside the
reason is written as ` - `. The first event replaces the line below.

No changes yet.
