# cairn
Curated Analysis, Insight and Recommendation Network

**A consulting analysis and synthesis framework built on LLM agents.**

Cairn helps consultants turn the large, mixed body of information in an engagement —
documents, decks, spreadsheets, images, interview notes and outside research — into a
traceable chain from evidence to recommendation that both the consultant and the client
can follow.

A cairn is a stack of stones that marks a trail. Cairn works the same way: every finding
is built on the cited evidence beneath it, and every engagement leaves markers — lessons —
for whoever comes next.

## How it works

- **Atomic, cited evidence.** Sources are broken into single observations, each linked to
  its original document, page or timestamp.
- **Traceable synthesis.** Observations build into findings, issues and opportunities,
  options and decisions. Any conclusion can be followed back to its evidence.
- **Never delete, supersede.** Ideas that change or are rejected keep their history and
  reasons, so negative lessons aren't repeated.
- **Agents propose, the consultant decides.** Agent output lands in a triage inbox;
  only the consultant promotes findings or releases content to the client.
- **One model, many views.** Working maps, change reports and client deliverables are
  all generated from the same underlying material.

## What's in the repo

- A folder convention for engagements, using plain markdown files with YAML front matter
- Templates for each object type (observation, finding, issue, option, decision, lesson)
- Agent skills for ingesting, extracting, synthesizing, researching, challenging and
  drafting deliverables. The first one, `charter`, ships in `src/cairn/assets/skills/`.

## Status

Early prototype. Phase 1 covers the core loop: charter, ingest, extract observations,
triage, synthesize, and what-changed.

## Creating an engagement

Cairn ships a small command, `cairn`, that creates engagement folders and keeps their
framework files up to date. It needs Python 3.11+ and uses only the standard library.

Install it from a checkout of this repo:

~~~bash
python3 -m pip install -e .        # inside a virtual environment, or:
uv tool install --editable .
~~~

Create an engagement **outside this repo** (the command refuses to create one inside the
framework checkout or inside another engagement):

~~~bash
cd ~/engagements
cairn init --engagement "Fulfillment Review" --client "Acme" --lead "Jane Analyst"
# → ./acme-fulfillment-review/ with the canonical folders, seed files, templates,
#   skills, and a local git repo with one commit (no remote)
~~~

Run `cairn init` with no options to be prompted for each value. Useful options:
`--code-name` (keeps the real client name out of folder names and every file except
`engagement.md`), `--model-use allowed|restricted|unconfirmed` (default `unconfirmed`),
`--merge` (add only missing items to an existing folder) and `--no-git`.

New engagements include the `charter` skill. Open the engagement folder in Claude Code and
run `/charter`: it interviews you to frame the scope, key questions, hypotheses,
assumptions, stakeholders and lenses, settles the model-use policy, and records later
revisions. It never reads client documents. Its helper script needs `python3` 3.9 or
later (the macOS system Python works); the `cairn` command itself still needs 3.11+.

When the framework gains new templates or skills, update an engagement with:

~~~bash
cd ~/engagements/acme-fulfillment-review
cairn refresh
~~~

Refresh only touches `_templates/` and the Cairn skills in `.claude/skills/`, asks before
replacing anything you edited (and backs it up), and never touches sources, charter,
objects, logs, views, deliverables or the inbox.

The framework assets live in the package: `src/cairn/assets/seed/` (README, engagement
record, charter and log files), `src/cairn/assets/templates/` (one template per object
type) and `src/cairn/assets/skills/` (Cairn skills, copied into each engagement).

For development: `python3 -m venv .venv && source .venv/bin/activate &&
python3 -m pip install -e '.[dev]' && python3 -m pytest`.
