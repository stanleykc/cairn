# Convention: Recording changes to Cairn objects

This document applies to `charter` now, and to `record-change`, `triage` and
`test-hypothesis` later (FR-030). The skill ships a byte-identical copy at
`skills/charter/reference/change-convention.md`. Any later skill that changes object
status ships its own identical copy, and a test enforces that the copies match.

## Principle

Ideas are never overwritten, only superseded or rejected with a reason (constitution
Principle VI). The changelog is the full history, and an object's own fields hold its
current state plus the reason for the latest change.

## Kinds of change

| Kind | When | What happens to the object(s) | Logged as |
|---|---|---|---|
| **Amend** | The object was created in the current session and is still `proposed` | Edited in place | not logged |
| **Clarify** | The wording changes but the claim doesn't | Title or body edited in place. Status and ID are unchanged. | `clarify`, with the previous wording quoted |
| **Supersede** | The claim changes (a sharper or different version) | New object: next free ID, `proposed`, `supersedes: [old]`, `change_reason`, `change_trigger`. On approval, new → `active`, old → `superseded`, and the reason and trigger are copied to the old object. | `supersede`, at approval |
| **Correct** | Like supersede, but the old claim was wrong (used by `record-change` when evidence disproves a claim) | as supersede | `correct`, at approval, with the quoted detail saying what was wrong |
| **Reject** | The consultant drops the object | `status: rejected`, with `change_reason` and `change_trigger`. Text kept. | `reject` |
| **Relink** | A link moves to a newer version (e.g. a hypothesis to a superseding question) | The link field changes on the moved object, and the old and new targets' back-link lists are updated. The claim is unchanged. | `relink`, with subject `H-003: Q-002 → Q-005` |
| **Scope change** | Text of a `scope.md` section that came from an earlier session is replaced | Section rewritten | `scope-change`, with the previous text quoted |

Also logged, without a trigger: `model-use` (the policy was set or changed) and
`approve-charter`.

## Rules

1. Nothing is ever deleted: no object, no entry, no changelog line.
2. Before writing a clarify, supersede, correct, reject, relink or scope change, get a
   **reason** (one line) and a **trigger**: `new evidence`, `client feedback` or
   `rethinking`. If either is missing, ask for it. Never invent one.
3. Only the consultant's explicit instruction changes a status. A new version stays
   `proposed`, and the old object is untouched until the new one is approved.
4. A `superseded` or `rejected` object isn't revised again. Point to its current version
   (follow `supersedes` links forward), or say it was dropped.
5. After a supersede, correct or reject, list every object that links to the changed one
   (by ID) for the consultant to review. A correct event must flag them all.
6. IDs are never reused. Links are IDs only.
7. Approving or rejecting never changes `audience`. `client-ready` is a separate consultant
   decision.

## Changelog line

~~~text
YYYY-MM-DD · <subject> · <event> · <reason> · <trigger>
> <detail line(s): previous text, what was wrong, what moved>
~~~

| Part | Values |
|---|---|
| date | the day the event was applied |
| subject | `Q-003` · `H-002 → H-004` · `H-003: Q-002 → Q-005` · `scope/Timeline` · `charter` · `model-use` |
| event | `supersede` · `correct` · `clarify` · `reject` · `relink` · `scope-change` · `model-use` · `approve-charter` |
| reason | one line. For `approve-charter`, write `approved by <name>`. For `model-use`, write `<old> → <new>` and the notes if any. |
| trigger | `new evidence` · `client feedback` · `rethinking` · `-` (for `model-use` and `approve-charter` only) |
| detail | required for `clarify` and `scope-change` (the previous text) and for `correct` (what was wrong). Optional otherwise. Every detail line starts with `> `. |

Separators are ` · ` (space, U+00B7, space). A literal ` · ` inside the reason is written
as ` - `. Events are appended newest last, and the first event replaces "No changes yet.".

### Examples

~~~text
2026-11-10 · H-002 → H-004 · supersede · narrowed to inbound receiving only · new evidence
2026-11-10 · A-001 · reject · carriers confirmed SLA penalties apply · client feedback
2026-11-10 · H-003: Q-002 → Q-005 · relink · follows Q-002 superseded by Q-005 · rethinking
2026-11-10 · scope/Timeline · scope-change · readout moved by sponsor · client feedback
> - 2026-12-04 — Final readout
2026-11-10 · Q-001 · clarify · plain-language wording · rethinking
> Why is order-to-ship time above target in the north DCs?
2026-11-03 · model-use · model-use · unconfirmed → restricted (no transcripts) · -
2026-11-03 · charter · approve-charter · approved by Test Lead · -
~~~
