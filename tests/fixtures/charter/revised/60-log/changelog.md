---
type: changelog
---

# Changelog

A dated record of every change to the engagement's ideas: supersede, correct, clarify,
reject, relink and scope change, plus model-use and charter approval. Nothing is deleted; a
changed idea is recorded here instead. The full convention is in
`.claude/skills/charter/reference/change-convention.md`.

Add one line per event, newest last:

`YYYY-MM-DD · <subject> · <event> · <reason> · <trigger>`

- subject: an ID (`A-###`), a new version (`<old ID> → <new ID>`), a moved link
  (`<H-ID>: <old Q-ID> → <new Q-ID>`), a scope section (`scope/Timeline`), `charter` or
  `model-use`
- event: `supersede · correct · clarify · reject · relink · scope-change · model-use · approve-charter`
- trigger: `new evidence · client feedback · rethinking · -` (`-` only for `model-use` and
  `approve-charter`)

Previous text, or what moved or was wrong, goes underneath in lines starting with `> `.
It is required for `clarify`, `scope-change` and `correct`. A literal ` · ` inside the
reason is written as ` - `. The first event replaces the line below.

2026-11-03 · model-use · model-use · unconfirmed → allowed · -
2026-11-03 · charter · approve-charter · approved by Test Lead · -
2026-11-10 · H-002 → H-004 · supersede · narrowed to weekday pickups after the week 44 data · new evidence
2026-11-10 · A-001 · reject · client expects 25% more volume from a new channel · client feedback
2026-11-10 · scope/Timeline · scope-change · final readout moved by the sponsor · client feedback
> - 2026-11-03 — Kickoff
> - 2026-11-20 — Diagnostic readout
> - 2026-12-04 — Final readout
