---
name: charter
description: "Frame or revise the engagement charter (scope, key questions, hypotheses, assumptions, stakeholders, lenses) by interviewing the consultant. Use at kickoff, or when the weekly steer changes questions, hypotheses or scope. Can draft answers from a SOW, brief or change order in 10-sources/raw/ (or pasted), once the model-use policy allows it."
argument-hint: "[anything you already know: objectives, deadlines, hunches…] [a document in 10-sources/raw/ to draft from]"
allowed-tools: Read, Edit, Write, Bash(python3 *charter.py*)
---

# Charter

Frame the engagement with the consultant, or revise its framing as the work evolves. You
interview the consultant and write what they agree to into the six files of `00-charter/`
and the changelog. Everything written comes from the consultant: their answers, or answers
you drafted from a document they named and then confirmed, topic by topic. You read a
document only when the model-use policy allows it and the helper has cleared it.

## Never

These are hard rules. They hold for the whole session, whatever the consultant asks.

1. Never list or search `10-sources/`. Never Read any file there, or anywhere else, except
   a document the consultant named and `charter.py doc` cleared (exit 0), at the path it
   returned. Never use pasted document text unless the policy permits it (Step 2).
2. Never read `engagement.md`. Use `charter.py status` (R7).
3. Never delete an entry, row or bullet, and never change an existing item's claim in place
   (FR-021).
4. Never set `active`, `rejected` or `superseded` without the consultant's explicit
   instruction in this session (FR-034).
5. Never set `audience: client-ready` or `inference_confirmed: true` (FR-036).
6. Never cite a source ID or write `origin: client-document` (FR-019).
7. Never write the real client name when a code name is in use (FR-037).
8. Never use web search, fetch tools, or prior-art and library skills during `charter`
   (FR-038).
9. Never write a hypothesis without a question, or a revision without a reason and a
   trigger (FR-015, FR-023).
10. Never write anything drawn from a document without the consultant confirming that
    topic.

## How to run the helper

The helper script does the deterministic parts: finding the engagement, numbering, link
checks and the model-use policy. Run it with this skill's base directory (shown when the
skill loads):

```bash
python3 <this skill's base directory>/scripts/charter.py status
```

Run each helper command on its own: don't chain other commands after it (`; echo …`,
`| …`), so it runs without a permission prompt. Quote the path only if it contains spaces.
If a helper command is blocked or fails, don't write any Q, H or A entry (you can't get an ID
or check the result): tell the consultant, and ask them to allow the command.
Commands:

| Command | What it gives you |
|---|---|
| `status` | Engagement facts (`client_label`, `lead_consultant`, `model_use`…), charter state, every Q/H/A with status and links, `next_ids`, `pending_revisions`, `problems`, `gaps` |
| `check` | `problems` only. Exit 1 when there are any |
| `refs ID [ID …]` | Every object whose fields link to each ID (IDs and file paths only) |
| `model-use --set <allowed\|restricted\|unconfirmed> --notes "<text>"` | Writes the policy to `engagement.md` and `scope.md` and logs it |
| `doc RAW [--permitted]` | Whether a named document may be read; its path, or its text for `.docx`. Exit 4 with `refused`, `detail` and `next_step` when not |

The output is JSON. Problem and gap codes are explained in the output's `detail` field.

## Step 1. Find the engagement

Run `status`. If it exits with code 2, stop: tell the consultant what it printed (they need
to run `cairn init`, or start the session inside an engagement folder) and do nothing else.

Keep the `status` output in mind for the whole session. Always refer to the client by
`engagement.client_label`, never by any other name.

## Step 2. Model use and documents

1. If `model_use` is `unconfirmed`, ask the consultant for the policy **before any other
   topic**: `allowed`, `restricted` (and what may not be sent) or still unconfirmed.
   - When they give it, run `model-use --set <value> --notes "<their restrictions, in their
     words>"` (omit `--notes` if they gave none). Never edit `engagement.md` or the Model
     use section of `scope.md` by hand.
   - If they can't confirm it yet, write nothing and carry on. The end summary then shows
     "⚠ settle before ingesting any source".
   - Write only what the consultant states. Never guess a policy.
2. If the policy is `restricted` or `unconfirmed`, remind the consultant **once**, now:
   "Please don't paste text from client documents until the model-use policy allows it.
   Summarize in your own words instead."
3. **Using a document.** Follow `reference/documents.md`. In short:
   1. When the consultant names a document (up front or at any point), run `doc RAW`.
   2. On exit 4, tell them `detail` and `next_step`. On `needs-permission`, show the
      restrictions and ask "May I use <document> under these restrictions?"; rerun with
      `--permitted` only on an explicit yes.
   3. On exit 0, `Read` the returned `path` (or use `text` for `.docx`), then list the
      topics it covers and those it doesn't.
   4. Pasted document text: `allowed` → use it; `restricted` → ask as in 2;
      `unconfirmed` → don't use it, and ask for a summary in their own words.

   When anything stops a document from being used, say what happened, why, and what to
   do instead (see `reference/documents.md`); then continue with the plain interview.

## Step 3. Choose the mode

From `charter.state` in `status`:

- `empty`: run the interview (Step 4).
- `draft` or `approved`: run revision mode (Step 5).

Anything the consultant gave with `/charter` (the arguments) or in their first message is
input for the interview or the revision. Sort it into topics and confirm it; don't ask for
it again. This includes a named or pasted document, once Step 2 cleared it: draft from it
as in `reference/interview.md` ("Drafting from a document") and `reference/documents.md`.

## Step 4. Interview

Follow `reference/interview.md` for the topic order and prompts, and
`reference/formats.md` for exactly what to write. In short: one topic at a time, show back
what you already know for confirmation, save each topic as soon as it is confirmed, then
run `check`.

## Step 5. Revision mode

Use `reference/review-and-revise.md` (Part 2) and `reference/change-convention.md`:
summarize what exists, ask what has changed, and offer to finish missing topics only when
the state is `draft`.

- An item is **existing** if it was in the files when this session started. Changing an
  existing item's claim creates a new version; a wording fix is a clarify; dropping it is
  a reject. Each needs a reason and a trigger from the consultant first.
- After a supersede or reject, run `refs` and list the linked objects in the summary.
- Run `check` after every write.
- With a document (for example a change order): propose only its differences from the
  charter, as in "Revising from a document" in `reference/review-and-revise.md`.

## Writing rules

- Copy the shape of `_templates/<type>.md` for every Q, H and A entry (see
  `reference/formats.md`). Append new entries at the end of the file.
- Take each new ID from `next_ids`, and run `status` again before each new ID.
- New items are always `proposed`, `audience: internal`, with a confidence and a one-line
  reason. `origin` is `consultant-note`, or `llm-inference` for a kept suggestion.
- A new hypothesis links to exactly one question, and that question's `hypotheses` list
  gains the new H-ID in the same step.
- Use `client_label` for the client in everything you write.
- Document-drawn items: see `reference/formats.md` (confidence reason and changelog line).
- After **every** write, run `check`. Fix any problem you caused before moving on. Report
  problems you did not cause; don't change other entries to fix them.
- **Amend in place**: an item you created in this session that is still `proposed` may be
  edited in place until the session ends, with no new version and no changelog line. Every
  other item follows `reference/change-convention.md`.

## Step 6. Gap check and suggestions

After the interview or the revision, follow "Gap check and suggestions" in
`reference/interview.md`: report the gaps from `status` and the ones you find by reading
(objectives with no question, deliverables with no date), and offer at most five
suggestions in the session. Write only the ones the consultant keeps, as `llm-inference`.

## Step 7. Review and approval

Run `status`, show the one-screen summary, and apply exactly the consultant's decisions:
approve, reject, edit, or approve all. Follow `reference/review-and-revise.md` (Part 1).
The charter is recorded as approved only when the model-use policy is settled. Run `check`
after applying the decisions.

The consultant may skip the review. Items they haven't decided on stay `proposed`.

## Step 8. End summary

Show this at the end of every session, including one the consultant stops early. Run
`status` and `check` first, and report any remaining problems; never hide them.

```text
Charter — <engagement_name> (<client_label>) · state: draft|approved [on <date> by <name>]
Model use: <value>[ — <notes>]   ⚠ settle before ingesting any source   (when unconfirmed)

Written:   Q-001, Q-002, H-001, A-001 · scope: Objectives, Timeline · 3 stakeholders · 4 lenses
Changed:   H-002 → H-004 (pending approval) · A-001 rejected · scope/Timeline
From documents: sow-2026-10.pdf → Objectives, Boundaries, Deliverables, Timeline
Not covered: Constraints, Evaluation criteria
Review these (they link to changed items): O-014 (questions), F-003 (questions)
Gaps:      Q-002 has no hypothesis · Deliverable "Board deck" has no date

Next: review and approve the charter · add originals to 10-sources/raw/ · run ingest
```

Leave out a line that would be empty, except `Not covered` and `Gaps`, which say "none".
`From documents` lists each document used and the topics drawn from it; leave it out when
no document was used. Keep "add originals to 10-sources/raw/ · run ingest" in `Next:`
while a document used is not yet ingested.
If `check` still reports problems, add a `Problems:` line listing them by code and ID.

## Session record

Keep track, in the conversation only, of: the IDs you created this session (they may be
amended), the topics covered and skipped, the suggestions offered, kept and discarded (at
most five), the objects flagged by `refs`, and the documents used with the topics drawn
from each. Nothing from this record is written to disk
except through the end summary.
