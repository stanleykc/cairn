# Writing observations

How to turn a source's words into observations that the script accepts and the consultant
can check in seconds. All examples are synthetic.

An observation is **one claim, from one source, with no interpretation**, plus the exact
passage it came from and where that passage is. If you can't point at the words that say
it, it isn't an observation.

## One claim per observation

A sentence often holds more than one claim. Split it, and cite the same passage from each
observation (send the second with `"accept_warnings": ["same-passage"]`):

> North 2 shipped 38,950 orders at 3.9 days to ship, the slowest of the northern sites,
> because one shift lead role is still open.

- O-1: "The FY25 operations review gives North 2's days to ship as 3.9."
- O-2: "The FY25 operations review says North 2 was the slowest of the northern sites."
- O-3: "The FY25 operations review says North 2 is the slowest because one shift lead role
  is still open."

The order count is a fourth claim; keep it only if it matters. A figure and its cause are
two claims (O-1 and O-3). So are a fact and an opinion about it.

Don't split a claim into pieces that mean nothing alone ("in both northern sites").

## No interpretation

Write only what the passage states. Each of these is refused by the reviewer, even when it
is probably true:

| Kind | Passage | Rejected claim | Why |
|---|---|---|---|
| Interpretation | "North 2: 3.9 days to ship." | "North 2 is the slowest site." | The passage doesn't compare sites. |
| Calculation | "North 1: 41,200 orders; North 2: 38,950 orders." | "The northern sites handled 80,150 orders." | You added them up. |
| Generalisation | "Cycle counts were skipped on two Fridays in September." | "Cycle counts are often skipped." | Two Fridays isn't "often". |
| Combining passages | p. 2 "Days to ship rose in Q3." + p. 3 "Two shift leads left in July." | "Days to ship rose after the shift leads left." | Two passages; the link is yours. |

Keep the source's own hedges and scope: "about", "provisional", "in the north sites",
"in Q3".

A claim that needs two separate passages is not an observation. Record each passage's
claim on its own, and mention the link in the summary under "Apparent conflicts" or leave
it for synthesis.

## Claim forms for documents

Say whose document it is, and give the claim as the document states it:

- Text: "The FY25 operations review says order-to-ship time rose in both northern sites
  during Q3."
- Table row: "The FY25 operations review gives North 2's days to ship as 3.9."
- Lists and steps: "The inbound process manual lists scanning every pallet label as a
  receiving step."
- Derived content (a chart description, OCR, chart data): say it is derived. "The chart
  description on p. 2 says the two lines rise between Q1 and Q3, then flatten in Q4." The
  script sets `derived: true`; the summary asks the consultant to check it against the
  original.

## Choosing the passage

- Quote the **whole sentence** (or the whole table row) that holds the claim, word for
  word. The script normalises whitespace, line breaks, `**`, `> ` and table pipes, and
  nothing else: punctuation, case and spelling must match.
- One contiguous passage. No `…` or `...`, no skipped words, no joined pieces.
- At least 3 words (a table row may be shorter).
- Never quote `## Context`, `## Description`, `## Speakers` or `## Uncertain passages`:
  they are the consultant's or `ingest`'s words, not the source's.
- A claim repeated in one source: one observation, citing the clearest occurrence.

## Locators

Use exactly a unit from `prepare`'s `units`:

| Source | Locator |
|---|---|
| PDF | `p. 2` (the `### p. n` marker, not the printed page number) |
| Word, markdown | `§ Receiving > Shifts` (the heading path); `¶ 3` for paragraphs before the first heading |
| Plain text | `¶ 12` |
| Transcript | `00:12:41` (the turn's timestamp) or `T17` when there are none |
| Word comment | `comment 1 @ § Receiving` |
| Footnotes | `footnotes` |

For a table row, add `› table n › row m`, and optionally `› <column header>`: tables are
counted from 1 within the unit, rows from 1 below the header.
`p. 2 › table 1 › row 2 › Days to ship`. A table-row quote with a bare `p. 2` is refused
(`table-locator-missing`).

## Confidence

One of `high`, `medium`, `low`, with a one-line reason ("client's own KPI table; method
not stated"). It can't exceed `prepare`'s `cap`:

- the source's own confidence;
- `medium` at most for AI note-taker notes;
- `low` on any locator listed in `uncertain_passages` (OCR, faint text, merged cells,
  tracked changes). The reason must say so; the script prefixes `uncertain extraction: `
  when it doesn't.

Lower it further when the passage itself is hedged ("about", "provisional") or second-hand.

## Titles

Up to 80 characters, a plain statement of the claim: "North 2 averages 3.9 days to ship".
Use the code name (`client_label`), never the real client name, in titles and claims. The
passage keeps the source's own words, whatever they are.

## Tagging and steering

- Tag every question the observation bears on, using only IDs from `status` (FR-017). Never
  create a question or a hypothesis; suggest `/charter` instead.
- With no focus, keep every factual claim. A claim that bears on no question goes in with
  `"questions": []` and is listed as "Untagged" (R1).
- With a focus, propose only claims that bear on a focus question, and tag each with at
  least one focus ID.
- A perspective changes which claims you favour, never the wording of a claim.

Examples for Q-003 "Why is fulfilment slow":

- In focus: "The draft fulfilment review says orders released after 3 pm miss the same-day
  carrier pickup." → `["Q-003"]`.
- Off focus: "The draft fulfilment review says the packing team at North 2 works one shift
  on Fridays." This is staffing (Q-002), not why fulfilment is slow, unless the source ties
  it to delay. With focus Q-003, drop it.

## Meetings and notes

### Transcripts

- Say who said it: "Dana Reyes said …". Use the confirmed name from `prepare`'s `speakers`
  when there is one, else the label as it appears ("Speaker 2 said …"). The script sets
  `speaker` and warns `attribution-missing` when the claim doesn't name them.
- Never state a speaker's claim as fact. Keep the kind of statement and the hedge:

| Passage | Claim |
|---|---|
| "I think the late orders are mostly from two key accounts." | "Lee said they think the late orders are mostly from two key accounts." |
| "We estimated that about a third of orders arrive after the cut-off." | "Dana Reyes said they estimated that about a third of orders arrive after the cut-off." |
| "Honestly, sales always sends the orders late, that's the whole problem." | "Speaker 2 said that sales always sends the orders late and called it the whole problem." |

  The last one is a sweeping claim about another team: say what was said, set confidence
  no higher than `medium`, and give the reason ("first-hand opinion about another team;
  not backed by data in the interview").
- A question is not a claim. "Have the shift leads been replaced?" is not evidence that
  they haven't.
- Locator: the turn's timestamp, or `T n` when the transcript has none.

### Meeting notes and summaries

A summary is a second-hand account. Say so, and whose:

- A colleague's notes: "The summary by Sam Okafor reports that the backlog at North 2 is
  down from last week."
- AI notes: "The AI notes by MeetBot report that the team agreed to pilot a second shift at
  North 2 starting in January." Confidence at most `medium`.

The script warns `summary-attribution-missing` when the claim names neither the author nor
"summary" or "notes".

### Comments and tracked changes

- A Word comment: "A reviewer comment by J. Ortiz asks whether this is still true since the
  new dock schedule." Locator `comment 1 @ § Receiving`.
- An unaccepted tracked change: "An unaccepted tracked change would make the text say
  pallets are checked against the ASN within two hours on arrival." Quote the text with its
  `{++ ++}` / `{-- --}` marks, exactly as in the source.

The script sets `passage_kind` and warns `kind-unstated` when the claim doesn't say
"comment" or "tracked change".

### Other languages

Quote the passage word for word in its own language. Write the claim in English, end it
with "(translated)", and set `"translated": true`.

## Conflicts

Two passages that disagree (in one source or two) are two observations. Don't link them and
don't pick a winner. Name the pair under "Apparent conflicts (not linked)" in the summary.
