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
  drafting deliverables. The first two, `charter` and `ingest`, ship in
  `src/cairn/assets/skills/`.

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
Accept Claude Code's trust prompt the first time you open the engagement: the engagement's
`.claude/settings.json` then lets the skill's helper run without asking each time.

New engagements also include the `ingest` skill. Once `/charter` has settled the model-use
policy, drop client material into `10-sources/raw/` and run `/ingest` inside the
engagement. It turns each file into a verbatim, citable source in `10-sources/extracted/`
(`S-###.md`) with your one line of context, and never changes the originals. Supported
formats: PDF, Word (`.docx`), markdown, plain text, and meeting transcripts (`.vtt`,
`.srt`, or text exports from Zoom, Teams, Meet and Otter). Under a `restricted` policy it
asks before sending each file, and restricted files are recorded without being opened.
`/ingest review` walks you through spot-checking, approving and correcting sources.
Installing poppler is recommended but not required (`brew install poppler` or
`apt install poppler-utils`): with it, PDF text is extracted and checked word for word;
without it, only PDFs of up to 10 pages can be ingested, and they are marked for
spot-checking. The helper needs `python3` 3.9 or later.

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
