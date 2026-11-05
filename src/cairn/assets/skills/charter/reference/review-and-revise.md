# Review and revision

Part 1 covers the review and approval at the end of a session. Part 2 covers revision
mode, used whenever a charter already exists. The rules for every change (reasons,
triggers, changelog lines) are in `reference/change-convention.md`; this file says how
`charter` applies them.

An item is **existing** if it was in the files when the session started. An item you
created this session that is still `proposed` may be edited in place (an *amend*), with
no new version and no changelog line.

## Part 1. Review and approval

### The one-screen summary

Run `charter.py status`, then show one compact screen:

```text
Charter — Fulfillment Review (Acme) · draft            Model use: restricted — No interview transcripts to external AI
Scope:  Objectives ✓ · In scope ✓ · Out of scope ✓ · Deliverables ✓ · Timeline ✓ · Constraints —
Questions:   Q-001 Why is order-to-ship slow… (proposed) · Q-002 Which steps drive… (active)
Hypotheses:  H-001 Slotting rules… → Q-001 (proposed) · H-004 → Q-002 (proposed, revises H-002)
Assumptions: A-001 Volumes stay near last year (proposed)
Stakeholders: 2 · Lenses: 4 · Criteria: 2
Pending revisions: H-004 replaces H-002
Gaps: Q-003 has no hypothesis · Deliverable "Final recommendations" has no date
```

- Scope by section (`✓` filled, `—` empty or missing), then each Q, H and A by ID, title
  and status. Show `rejected` and `superseded` items only as a count unless asked.
- Pending revisions come from `pending_revisions`.
- When `charter_status` is `approved`, add "N items proposed since approval on
  <approved_on>" (from `proposed_since_approval`).
- Then ask what the consultant wants to do: approve, reject, edit, or approve all.

### Applying decisions

Apply **only** what the consultant explicitly says. Everything without an instruction stays
`proposed`. Never change `audience`, and never set `client-ready`.

- **Approve** an item: `status: proposed` → `active`. Nothing is logged.
- **Approve a pending revision** (`H-004` revises `H-002`): apply it as in Part 2,
  "Approving a new version".
- **Reject** an item: if the consultant gave no reason or trigger, ask for them. Then set
  `status: rejected`, `change_reason: "<reason>"`, `change_trigger: <new-evidence |
  client-feedback | rethinking>`, keep the title and text exactly as they are, and append:

  ```text
  YYYY-MM-DD · H-001 · reject · <reason> · <trigger>
  ```

  Then run `charter.py refs H-001` and list any objects that link to it.
- **Edit** an item: if you created it this session and it is still `proposed`, amend it in
  place. Otherwise it is a clarify (wording only) or a new version (the claim changes):
  see Part 2.
- After each change, run `charter.py check`.

### Approve all (approving the charter)

1. List every item that will change: each `proposed` Q, H and A, and each pending
   revision (with the item it replaces). Ask the consultant to confirm the list. If they
   want to hold an item back, it must be rejected (with a reason), or the approval put
   off.
2. Ask who is approving. Default to `lead_consultant` from `status`, and confirm it.
3. On confirmation:
   - every `proposed` Q, H and A becomes `active`; pending revisions are applied as in
     Part 2 (new → `active`, old → `superseded`, one `supersede` line each);
   - if `model_use` is `allowed` or `restricted`: in `scope.md` front matter set
     `charter_status: approved`, `approved_on: "<today>"`, `approved_by: "<name>"`, and
     append `YYYY-MM-DD · charter · approve-charter · approved by <name> · -`;
   - if `model_use` is `unconfirmed`: the items still become `active`, but leave
     `charter_status: draft`, write no approval and no `approve-charter` line, and tell
     the consultant the charter can only be approved once the model-use policy is
     settled (offer to settle it now with `charter.py model-use`).
4. Approving again later (after revisions) updates `approved_on` and `approved_by` and logs
   another `approve-charter` line. Revisions never reset `charter_status` to `draft`.
5. Run `charter.py check`.

## Part 2. Revision

### Opening in revision mode

When `charter.state` is `draft` or `approved`:

1. Summarize what exists, from `status`: the scope sections filled, the Q, H and A by ID
   and title with their status, pending revisions, and the counts of stakeholders and
   lenses. Keep it short.
2. Ask what has changed since the last session: new questions, sharper hypotheses,
   assumptions that proved wrong, scope changes.
3. If the state is `draft` and topics are still missing (empty scope sections, no
   questions, no stakeholders, no lenses), offer to finish those topics with the interview
   (`reference/interview.md`), for the missing topics only.

Do not run the full interview again, and never ask for something already recorded.

### Reason and trigger first

Before writing any clarify, new version, reject, relink or scope change, you need:

- a **reason**: one line, in the consultant's words;
- a **trigger**: `new evidence`, `client feedback` or `rethinking`.

If either is missing, ask for it. Never invent one, and write nothing until you have both.
In the item's fields the trigger is written with hyphens (`new-evidence`,
`client-feedback`, `rethinking`). In the changelog it is written with spaces.

### Adding an item

A new question, hypothesis or assumption is written exactly as in the interview: next free
ID, `proposed`, `consultant-note`. A new hypothesis still needs exactly one question, and
its H-ID goes into that question's `hypotheses` list at once. Nothing is logged for an
addition.

### A new version (the claim changes)

For an existing item whose claim changes (for example `H-002`):

1. Create a new entry with the next free ID (for example `H-004`): `status: proposed`,
   `supersedes: ["H-002"]`, `change_reason: "<reason>"`, `change_trigger: <trigger>`.
   Copy the other fields from the old item unless the consultant changes them. A new
   hypothesis keeps the same `question` unless the consultant says otherwise, and its H-ID
   is added to that question's `hypotheses` list now.
2. Leave the old item **completely untouched**. Nothing is logged yet.
3. The new version is now a pending revision until the consultant decides.

**Approving a new version**: set the new item `active`, then set the old item
`status: superseded` and copy the new item's `change_reason` and `change_trigger` onto it.
Append one line:

```text
YYYY-MM-DD · H-002 → H-004 · supersede · <reason> · <trigger>
```

**Rejecting a new version**: set only the new item `rejected`, with its own
`change_reason` and `change_trigger` (ask for them). The old item stays as it was. Append:

```text
YYYY-MM-DD · H-004 · reject · <reason> · <trigger>
```

### Clarify (wording only, same claim)

Edit the title (heading and `title` field) or the body in place. Status and ID stay the
same. Append a `clarify` line with the previous wording quoted:

```text
YYYY-MM-DD · Q-001 · clarify · plain-language wording · rethinking
> Why is order-to-ship time above target in the north DCs?
```

If you are unsure whether the claim changes, ask the consultant: clarify or new version?

### Reject an existing item

As in Part 1: `status: rejected`, `change_reason`, `change_trigger`, text kept, one `reject`
line.

### Scope change

Replacing a scope section that holds content from an earlier session: rewrite the whole
section in `scope.md`, then append a `scope-change` line with the previous text quoted,
one `> ` line per original line:

```text
YYYY-MM-DD · scope/Timeline · scope-change · readout moved by sponsor · client feedback
> - 2026-11-03 — Kickoff
> - 2026-12-04 — Final readout
```

Constraints are part of scope: changing them is a scope change too (subject
`scope/Constraints`). Filling a section that still held seed guidance is not a scope
change and is not logged.

### Revising from a document

When the consultant names a document in revision mode (a change order, a revised SOW),
first clear and read it as in `reference/documents.md`. Then:

1. Compare it with the `status` output and the charter files. List **only the
   differences**: what the document adds, moves or contradicts. Never re-propose what the
   charter already says.
2. If there are no differences, say "No changes found in <document>" and write nothing
   (G15).
3. Propose each difference **one at a time**, under `reference/change-convention.md`: a
   new item, a new version, a clarify, a reject or a scope change, as the difference
   requires. Nothing is written until the consultant confirms it.
4. Each needs a reason and a trigger, as always. The reason comes from the consultant, or
   from the document's own stated reason once the consultant confirms it. The trigger is
   still one of `new evidence`, `client feedback` or `rethinking` (ask; a change order from
   the client is usually `client feedback`). Name the document in the reason:
   `<reason> (new document: <document name>)`, for example

   ```text
   2026-11-12 · scope/Timeline · scope-change · offsite moved (new document: change-order-1.md) · client feedback
   > - 2026-12-04: Final readout.
   ```

5. If the document conflicts with the charter and the consultant disagrees with the
   document, the consultant's answer wins (G13).
6. After the changes, append the `drew … from <document name> (consultant confirmed)` line
   (`reference/formats.md`) only for topics added from the document, not for changes
   already logged above.

### Objects that link to a changed item

After a supersede (at approval) or a reject, run `charter.py refs <ID>` for each changed
item, and list every object returned, by ID and field ("O-014 (questions), F-003
(derived_from)"), in the summary under "Review these". Do not open those objects.

### When a question gets a new version

When a new version of a question is approved (`Q-002` → `Q-005`), list the `active` and
`proposed` hypotheses whose `question` is the old one, and ask, for each, whether it moves
to the new question. For each one that moves:

- set the hypothesis's `question` to the new Q-ID (its claim and status are unchanged);
- add the H-ID to the new question's `hypotheses`;
- remove the H-ID from the old question's `hypotheses` (the only edit ever made to a
  superseded item);
- append `YYYY-MM-DD · H-003: Q-002 → Q-005 · relink · <reason> · <trigger>`.

Hypotheses that don't move stay linked to the old question.

### Superseded and rejected items

A `superseded` or `rejected` item is never edited again (except the relink removal above).
If the consultant asks to revise one:

- superseded: follow the `supersedes` links forward to the current version, say which it
  is ("H-002 was replaced by H-004"), and ask whether to revise that instead;
- rejected: say it was dropped, with its `change_reason`, and ask how to proceed (for
  example, add a new item).
