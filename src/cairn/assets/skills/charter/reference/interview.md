# Interview: framing the charter topic by topic

Use this when `charter.state` is `empty`, or when the consultant wants to finish topics
still missing from a `draft` charter. Formats for everything written are in
`reference/formats.md`.

## Before the first topic

1. **Anything given up front.** If the consultant typed something after `/charter` (or in
   their first message), sort it into the topics below before asking anything. For each
   topic it covers, show back what you captured ("I have the objective as: … and the final
   readout as 2026-12-04. Is that right?") and ask them to confirm or correct it. Never ask
   them to restate it.
2. **Earlier answers.** The same applies all through the session: when an earlier answer
   already covers a topic, show it back for confirmation instead of asking again.
3. **Minimum for a draft.** Objectives and at least one key question. Every other topic
   may be skipped. Keep a list of skipped topics for the end summary.

## Topic order

Cover one topic at a time, in this order. Each prompt is a starting point: keep it short,
and use the consultant's own words in what you write.

| # | Topic | Prompt | Written to |
|---|---|---|---|
| 1 | Objectives | "What does the client need from this engagement? A few bullets is plenty." | `scope.md` → Objectives |
| 2 | Boundaries | "What's in scope, and just as important, what's out?" | `scope.md` → In scope / Out of scope |
| 3 | Deliverables | "What will you hand over, in what form, and when is each due?" | `scope.md` → Deliverables |
| 4 | Timeline | "What are the key dates: kickoff, interviews, readouts, final delivery?" | `scope.md` → Timeline |
| 5 | Constraints | "Any constraints I should record: budget, timeline, technology, politics?" | `scope.md` → Constraints |
| 6 | Key questions | "What are the key questions this engagement must answer?" | `questions.md` |
| 7 | Hunches | "Any early hunches about the answers?" | `hypotheses.md` |
| 8 | Assumptions | "What are you taking as true without evidence yet?" | `assumptions.md` |
| 9 | Stakeholders | "Who's involved: name, role, their view of the problem?" | `stakeholders.md` |
| 10 | Lenses and criteria | Offer the starting lenses (below), then ask for evaluation criteria | `lenses.md` |

## Saving as you go

- Save each topic **as soon as the consultant confirms it**, before moving to the next
  one. Stopping partway must lose nothing already agreed.
- After each save, run `charter.py check`. If it reports a problem you caused, fix it
  before moving on. Never "fix" problems in entries you didn't write this session: report
  them instead.
- Run `charter.py status` before each new Q/H/A, and take the ID from `next_ids`.

## Topic notes

**Key questions.** Each question gets a title, a one- or two-sentence statement, a
priority (if the consultant gives one) and who raised it. If the consultant names more
than about ten, record them all, then suggest marking priorities so the work stays
focused.

**Question or hunch?** If a "question" is really a hunch ("I bet it's the slotting rules"),
or a "hunch" is really a question, say so and suggest the other type. The consultant
decides.

**Hunches become hypotheses.** Questions come first, so that each hunch can be tied to
exactly one question as it is recorded:

- Ask which question it answers if that isn't obvious.
- If it fits no question, offer a question that it would answer ("Should I add a question
  like 'Which steps drive the delay?' for this?"), or ask "Which question does this
  answer?". Never write a hypothesis without a question.
- Ask what evidence would confirm it and what would reject it. Write them to `confirm_if`
  and `reject_if`.
- Write the hypothesis and add its H-ID to the question's `hypotheses` list in the same
  step.

**Assumptions.** Record the `basis` (why it is taken as true) and the `questions` it
affects.

**Stakeholders.** Interview status defaults to `not yet interviewed`. If the consultant
mentions something sensitive about a person (credibility, politics, conflicts), ask
whether it should be written down before putting it in Perspective. The charter stays
`internal` either way.

**Lenses and criteria.** Offer this starting set, which the consultant can accept, change
or replace:

- **Cost**: cost to serve and the cost of each change.
- **Risk**: operational, delivery and change risk.
- **Customer experience**: what the client's customers see and feel.
- **Operating model**: roles, processes and governance.

Then ask which criteria options will be judged against (for example time to value, ease
of adoption). Lens and criterion names must be unique within their section.

## Gap check and suggestions

Run this after the interview or a revision, before the review.

1. Run `charter.py status` and read `gaps`:
   - `question-no-hypothesis`, `hypothesis-no-reject`, `hypothesis-no-confirm`,
     `assumption-no-basis`, `scope-section-empty` (with `section`), `no-stakeholders`,
     `no-lenses`, `many-questions`.
2. Read `scope.md`, `questions.md` and the deliverables yourself, and also find:
   - objectives that no `proposed` or `active` question addresses;
   - deliverables with no date (`date TBD` counts as no date).
3. Report the gaps briefly, by ID or by name ("Objective 'operating model without new
   headcount' has no question").
4. **Suggestions.** You may offer at most **five** suggested questions, hypotheses or
   assumptions in the whole session, counting both kept and discarded ones. Show each one
   to the consultant **before** writing anything, and ask: keep or discard?
   - **Keep**: write it like any other entry, with `origin: llm-inference`,
     `status: proposed`, `inference_confirmed: false`, and a `confidence_reason` starting
     "Suggested by `charter`:" (for example
     `"Suggested by \`charter\`: covers the headcount objective"`). A kept hypothesis
     still needs exactly one question, and its H-ID goes into that question's
     `hypotheses`.
   - **Discard**: write it nowhere, not in any file and not in the changelog.
5. List the gaps that remain on the `Gaps:` line of the end summary.
