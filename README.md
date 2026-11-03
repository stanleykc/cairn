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
  drafting deliverables

## Status

Early prototype. Phase 1 covers the core loop: charter, ingest, extract observations,
triage, synthesize, and what-changed.
