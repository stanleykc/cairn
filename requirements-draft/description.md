# Consulting Analysis & Synthesis Framework

Nov 2, 2026 · @Kevin Stanley

Cairn turns the scattered material of a consulting engagement into a traceable path from cited evidence to client recommendations, built with LLM agents and governed by the consultant. The name comes from the stacked stones hikers build to mark a trail: each finding is built on the evidence beneath it, and each engagement leaves markers (lessons) for the next.
## Purpose and problem

This framework uses LLM agents to turn the large, mixed body of information in a consulting engagement into a traceable chain from evidence to recommendation that both the consultant and the client can follow.

The problem it addresses:

- **Volume and variety.** Engagements produce PDFs, slide decks, spreadsheets, images, interview notes and outside research. Each needs its content extracted before it can be used.
- **Coherence.** Insights are scattered across documents. It is hard to see how an observation in one source connects to an issue, an option or a conclusion.
- **Evolving ideas.** Ideas churn, branch and get abandoned. The reasons behind those changes are lost, so the same mistakes get revisited.
- **Two audiences.** The working picture the consultant needs is different from the clear narrative the client needs, and both must stay consistent.

The framework is designed as an assistant to the consultant's judgment, not a replacement for it. Agents collect, extract, connect and draft; the consultant decides what is true, what matters and what the client sees.

## Design principles

1. **Atomic, cited evidence.** The smallest unit of work is an observation: one statement taken from one source, with a citation. Everything else is built from observations.
2. **Traceability by construction.** Every finding, issue, option and recommendation links down to the observations that support it. Any conclusion can be checked against its evidence.
3. **Provenance is always visible.** Each item records where it came from (client document, interview, external research, or LLM inference) and how confident we are in it.
4. **Never delete, supersede.** Ideas are not overwritten. They are marked superseded or rejected, with a reason, so the history of thinking is kept.
5. **Hypothesis-driven.** Key questions and working hypotheses steer what gets researched and extracted.
6. **One model, many views.** Working views and client deliverables are generated from the same underlying material, so they stay consistent.
7. **Agents propose, the consultant decides.** Promotion of findings, acceptance of recommendations and release to the client are explicit human decisions.
8. **Start with files, not a platform.** The first version is a folder convention, markdown files with metadata and a set of agent skills. A platform is built only once the data model has been proven on real engagements.

## Architecture overview

The framework has three layers: agent skills that propose work, a data model that holds cited evidence and conclusions, and views generated from that model for each audience.

&#91;embedded content: framework architecture · 3 layers\]
![[Pasted image 20261102120223.png]]

Work flows upward. Skills write proposed items into the model, the consultant's review makes them active, and every view is generated from active items rather than written separately.

## Data model

The framework tracks nine object types, connected by five relationships, each with a status and provenance. This replaces the original analysis categories, which mixed objects (solutions, tools), views (summaries) and changes (clarifications, corrections).

### Object types

| Type | What it is | Built from | Replaces original category |
| --- | --- | --- | --- |
| Source | An original document, transcript, image or web page, kept unchanged | — | — |
| Observation | One cited statement taken from a source | Source | — |
| Question | Something the engagement needs to answer | Charter, client | — |
| Hypothesis | A working answer to a question, to be tested | Question | — |
| Assumption | Something taken as true without direct evidence | Consultant | — |
| Finding | An insight or implication drawn from several observations | Observations | Implications |
| Issue / Opportunity | A problem to solve or an advantage to exploit | Findings | — |
| Option | A possible solution, tool or enabler for an issue or opportunity | Issues, prior work, research | Solutions, Tools |
| Decision / Lesson | What was chosen or rejected, and why; positive and negative lessons | Options | Negative and positive lessons |

Summaries become **views** generated from these objects. Clarifications and corrections become **events** recorded against an existing object (see Managing evolving ideas).

### Relationships

| Relationship | Meaning | Example |
| --- | --- | --- |
| supports | Evidence for a finding, hypothesis or option | Observation supports Finding |
| contradicts | Evidence against | Interview observation contradicts a policy document |
| derived from | One idea grew out of another | Option B derived from Option A |
| supersedes | Replaces an earlier version or idea | Finding v2 supersedes Finding v1 |
| clarifies | Adds precision without changing the claim | Client follow-up clarifies an observation |

### Status and provenance fields

Every object carries:

- **Status:** proposed (agent or consultant drafted, unreviewed) · active · superseded · rejected.
- **Origin:** client document · interview / meeting · external research · prior engagement · LLM inference · consultant suggestion.
- **Confidence:** high · medium · low, with a one-line reason.
- **Audience:** internal only · client-ready.
- **Links:** IDs of the objects it supports, contradicts, derives from, supersedes or clarifies.

An item with origin *LLM inference* can never be client-ready until the consultant confirms it against a source.

## Pipeline from source to deliverable

Material moves through seven stages, each run by an agent skill and closed by a consultant review where judgment matters.

| # | Stage | What happens | Skill | Consultant gate |
| --- | --- | --- | --- | --- |
| 1 | Frame | Record scope, key questions, hypotheses, stakeholders | `charter` | Approves the charter |
| 2 | Ingest | Store originals; convert each to markdown with metadata; index | `ingest` | Spot-checks image and table extraction |
| 3 | Extract | Pull atomic, cited observations from each source | `extract-observations` | Reviews the triage inbox |
| 4 | Research | Targeted external and prior-work research tied to questions | `research-question`, `find-prior-art` | Accepts or discards results |
| 5 | Synthesize | Group observations into findings, issues and opportunities; test hypotheses | `synthesize`, `test-hypothesis`, `find-contradictions` | Promotes findings to active |
| 6 | Propose | Draft options for each issue or opportunity, with evidence and lessons | `propose-options` | Accepts, rejects or reworks options |
| 7 | Communicate | Generate client views, change reports and deliverables | `what-changed`, `draft-deliverable` | Releases content to the client |

The stages are not strictly sequential. New sources arrive throughout, and synthesis is rerun as evidence builds. Stage 3 to 6 loops are expected.

## Managing evolving ideas and lessons

All change is recorded as an event on an object rather than an edit that erases the old version. One rule covers churn, derivations and lessons: **ideas are never overwritten, only superseded or rejected with a reason.**

| Original concern | How the framework handles it |
| --- | --- |
| Churn | A new version supersedes the old one; both stay in the log with the date and the trigger (new evidence, client feedback, rethinking) |
| Derivations | A *derived from* link records lineage, so a branch of thinking can be traced back to its origin |
| Negative lessons | A rejected option or hypothesis keeps its rationale and the evidence that sank it; agents check new options against it |
| Positive lessons | An accepted decision is tagged as a lesson to continue or extend, with the evidence it worked |
| Clarifications | A *clarifies* event refines an object without changing its claim |
| Corrections | A *supersedes* event replaces a wrong claim, records what was wrong, and flags every object built on it for review |

The most valuable output of this log is a **what changed** report: what is new, what moved, and what was dropped since a given date. It is the basis for status updates and client meetings.

## Audiences and views

The consultant and the client see different views of the same model; no client deliverable is written separately from it.

| View | Audience | Shape | Includes |
| --- | --- | --- | --- |
| Working map | Consultant | Linked graph and indexes | Everything, including proposed, rejected and low-confidence items |
| Evidence trail | Consultant, reviewers | Drill-down from any conclusion to its sources | Links, citations, origin and confidence |
| What changed | Consultant, then client | Dated change report | New, revised and dropped items since a date |
| Client narrative | Client | Pyramid: a few key messages, each backed by findings | Active, client-ready items only |
| Deliverables | Client | Report, deck, workshop material | Generated from the client narrative |

The client narrative passes a release filter: only active items marked client-ready, with confidential and unconfirmed material removed.

## Human-in-the-loop governance

Agents may create anything as *proposed*; only the consultant can make an item active, accepted or client-ready.

| Agents do on their own | The consultant decides |
| --- | --- |
| Ingest, convert and index sources | Whether a source is in scope |
| Extract observations with citations | Which observations are wrong or irrelevant |
| Run research tied to an open question | Whether research results are credible |
| Group evidence, flag contradictions, draft findings | Which findings become active |
| Draft options and check them against past lessons | Which options are accepted or rejected, and why |
| Generate views and draft deliverables | What is released to the client |

New agent output lands in a **triage inbox** (`_inbox/`). Reviewing it is a short daily habit: accept, edit, reject, or leave a question for later.

## Prototype folder structure

Each engagement is one folder of plain markdown files with YAML front matter, so it works in any editor (Obsidian, VS Code) and any agent can read and write it.

```
<client>-<engagement>/
  README.md                  engagement overview and how to use this folder
  _inbox/                    agent output awaiting consultant review
  00-charter/
    scope.md                 objectives, boundaries, deliverables, timeline
    questions.md             key questions (Q-###)
    hypotheses.md            working hypotheses (H-###), linked to questions
    assumptions.md           assumptions (A-###)
    stakeholders.md          people, roles, perspectives, interview status
    lenses.md                reusable analysis lenses and evaluation criteria
  10-sources/
    raw/                     originals, never modified (PDF, PPTX, XLSX, images, audio)
    extracted/               one markdown file per source (S-###), with metadata
    index.md                 catalogue of sources: title, type, date, origin, status
  20-research/               external and prior-work research (R-###), each tied to a question
  30-observations/           atomic, cited statements (O-###), one per file or grouped by source
  40-synthesis/
    findings/                insights and implications (F-###)
    issues/                  problems to solve (I-###)
    opportunities/           advantages to exploit (P-###)
  50-options/                solutions, tools and enablers (X-###), including rejected ones
  60-log/
    decisions.md             decisions and their rationale (D-###)
    lessons.md               positive and negative lessons (L-###)
    changelog.md             dated record of supersede, clarify and correct events
  70-views/                  generated views: evidence map, what-changed reports
  80-deliverables/           client-facing drafts and released versions
  _templates/                one template per object type
```

### Conventions

- **IDs.** Every object has a short, permanent ID with a type prefix (O-042, F-007). Links between objects use IDs, so files can be renamed or moved.
- **One object, one file** for findings, issues, opportunities and options, so each can be versioned and linked. Observations may be grouped per source for volume.
- **Originals stay untouched** in `raw/`. All work happens on the extracted markdown, which records the extraction method (text, OCR, vision description) and flags anything uncertain.
- **Status lives in front matter**, not in folder location, so moving files never changes meaning.

### Example object file

An observation, as an agent would write it:

```markdown
---
id: O-042
type: observation
source: S-011
locator: "p. 14, table 3"
origin: client-document
confidence: high
status: proposed
audience: internal
supports: [F-007]
contradicts: [O-019]
created: 2026-11-02
---
Order-to-ship time averaged 9 days in Q3, against a 5-day target.
```

## Agent skills to implement

Sixteen skills cover the pipeline; six of them make up the first usable version. Each skill is a folder of instructions (a SKILL.md plus templates or scripts) that an agent loads when the task matches.

### Skill catalogue

| Skill | Purpose | Reads | Writes | Phase |
| --- | --- | --- | --- | --- |
| `charter` | Interviews the consultant to set scope, key questions, hypotheses, assumptions and stakeholders | Consultant input, kickoff material | `00-charter/` | 1 |
| `ingest` | Converts each original to markdown with metadata; OCR and vision description for images; splits transcripts by speaker; updates the source index | `10-sources/raw/` | `10-sources/extracted/`, `index.md` | 1 |
| `extract-observations` | Pulls atomic, cited observations from a source and tags them to questions | Extracted sources, questions | `_inbox/` → `30-observations/` | 1 |
| `triage` | Presents the inbox for review and applies accept, edit, reject or defer | `_inbox/` | Status changes, files moved into place | 1 |
| `synthesize` | Groups observations into findings, issues and opportunities, each linked to its evidence | Observations, findings | `_inbox/` → `40-synthesis/` | 1 |
| `what-changed` | Reports what is new, revised and dropped since a date | All objects, `changelog.md` | `70-views/` | 1 |
| `research-question` | Runs web research for one question or hypothesis and records cited results | Questions, hypotheses | `20-research/` | 2 |
| `find-prior-art` | Searches past engagements for similar problems, solutions and lessons, anonymized | Firm library, `lessons.md` | `20-research/` | 2 |
| `test-hypothesis` | Gathers evidence for and against a hypothesis and proposes a verdict | Hypotheses, observations, findings | Hypothesis status, `_inbox/` | 2 |
| `find-contradictions` | Flags conflicting observations and stakeholder disagreements | Observations, stakeholders | `_inbox/`, contradicts links | 2 |
| `record-change` | Records supersede, clarify or correct events and flags every object built on a changed one | Any object | `changelog.md`, review flags | 2 |
| `debrief` | Interviews the consultant after a meeting to capture what was heard, what surprised them and what they doubted | Consultant answers, stakeholders, questions | `_inbox/` (consultant-note observations) | 2 |
| `propose-options` | Drafts options for an issue or opportunity and checks them against past lessons and rejected options | Issues, opportunities, lessons, research | `_inbox/` → `50-options/` | 3 |
| `challenge` | Argues against a finding or option using contradicting evidence and past negative lessons | Findings, options, observations, lessons | `_inbox/` (objections and gaps) | 3 |
| `draft-deliverable` | Builds the client narrative and a deliverable from client-ready items only | Active findings and options, charter | `80-deliverables/` | 3 |
| `check-traceability` | Verifies every claim in a draft traces to evidence; reports broken links, orphans and unconfirmed inferences | Deliverables, all objects | `70-views/` report | 3 |

### Rules every skill follows

- Never modify anything in `10-sources/raw/`.
- Cite every claim with a source ID and a locator (page, slide, timestamp, URL).
- Mark anything the model inferred, rather than read, as origin *LLM inference*.
- Write new objects as *proposed*, to `_inbox/` where shown, using the templates in `_templates/`.
- Assign IDs from the next free number for that type, and link by ID only.
- Never mark an item client-ready; only the consultant does that.

### Notes on the harder skills

- **ingest** carries most of the format risk. Charts, diagrams and photos of whiteboards should get both OCR text and a written description, flagged as derived. Spreadsheets should keep tables as tables, not prose.
- **extract-observations** must stay atomic: one claim per observation, no interpretation. Interpretation belongs in findings.
- **synthesize** should state the “so what” of each finding in one sentence and list every supporting and contradicting observation.
- **find-prior-art** can wrap the firm's existing OCI library skills (find prior art, ask the library) rather than being built from scratch, as long as client-identifying details are removed.

## Analyst workflow

The analyst works in a short loop of feeding material in, reviewing what agents propose, and steering the next round. Synthesis quality depends mostly on the steering context the analyst adds, not on the documents alone.

Interaction is conversational: the analyst invokes a skill in plain language or as a slash command (for example, `/synthesize Q-003 through a cost lens`). The analyst can also edit the markdown files directly, and anything written by hand counts as fully as agent output.

### Working rhythms

| Rhythm      | When                                | What the analyst does                                                         | Skills                                                                                   |
| ----------- | ----------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Set up      | Once, at kickoff                    | Answers a short interview on scope, questions, hunches and constraints        | `charter`                                                                                |
| Feed        | After every meeting or new document | Drops files in with a line of context each; is debriefed after meetings       | `ingest`, `extract-observations`, `debrief`                                              |
| Triage      | Daily, about 15 minutes             | Accepts, edits or rejects proposed items, with a reason for each reject       | `triage`                                                                                 |
| Steer       | Weekly, or when a question matures  | Revises questions and hypotheses; asks for synthesis, research or a challenge | `synthesize`, `test-hypothesis`, `research-question`, `find-contradictions`, `challenge` |
| Communicate | Before a client touchpoint          | Requests the change report and a draft, then checks traceability              | `what-changed`, `draft-deliverable`, `check-traceability`                                |

### Steering inputs

Seven kinds of input do the most to widen and deepen the synthesis. Without them, agents produce generic summaries.

1. **Intent:** which question or hypothesis the work serves. “Extract what bears on Q-003, why fulfillment is slow” beats “extract observations.”
2. **Lens:** the perspective to analyze through, such as cost, risk, customer experience, operating model, or a named framework like value chain or jobs-to-be-done. Running the same evidence through two lenses is one of the cheapest ways to widen the synthesis.
3. **Tacit knowledge:** what the analyst knows but nobody wrote down, such as hallway comments, politics, history, or who is credible. It is recorded as observations with origin *consultant note*.
4. **Judgment signals:** what seems important, what is doubtful, and hunches. Hunches become hypotheses, so agents look for evidence both for and against them.
5. **Scope:** which sources, stakeholders, dates or business units to include or exclude.
6. **Ambition:** conservative or exploratory, how many findings or options, and whether to range from incremental to transformational.
7. **Reasons:** why something is rejected, revised or superseded. These reasons become the negative lessons that keep later rounds from repeating mistakes.

Frequently used lenses and evaluation criteria are kept in `00-charter/lenses.md`, so a request can name them instead of retyping them.

### Inputs per skill

| Skill | Analyst must provide | Analyst can add to improve the result |
| --- | --- | --- |
| `charter` | Brief or statement of work; objectives | Known stakeholders, deadlines, LLM-use restrictions, early hunches |
| `ingest` | The files | Who provided each, why, how trustworthy, confidentiality, which sections matter |
| `debrief` | The meeting just held | Attendees, the agenda, anything that surprised or bothered the analyst |
| `extract-observations` | Source ID(s) | Questions to focus on, what to ignore, stakeholder perspective |
| `triage` | A verdict on each item | A one-line reason for every reject or edit |
| `synthesize` | Scope: a question, theme, or everything since a date | Lens, suspected patterns, conservative or bold, number of findings |
| `research-question` | Question or hypothesis ID | What is already known, preferred sources, industries, regions, time window |
| `find-prior-art` | Problem description | Industry, client type, and whether approaches, outcomes or pitfalls are wanted |
| `test-hypothesis` | Hypothesis ID | What evidence would change the analyst's mind |
| `find-contradictions` | Scope | Which stakeholder groups or sources to compare |
| `challenge` | Finding or option ID | The strongest objection the client is likely to raise |
| `record-change` | Object ID and type of change | Reason and trigger (new evidence, client feedback, rethinking) |
| `propose-options` | Issue or opportunity ID | Constraints (budget, timeline, technology, politics), criteria and weights, client appetite for change, options already ruled out |
| `what-changed` | Since date | Audience: internal or client |
| `draft-deliverable` | Audience and purpose (the decision it supports) | Format, length, key messages or a request to propose them, tone, exclusions |
| `check-traceability` | The draft | Strictness: flag only, or block release |

### Example steering session

> **Analyst:** `/synthesize Q-003` using an operating-model lens. I suspect the slowdown is in handoffs between sales and the warehouse, not in the warehouse itself. Be exploratory; up to five findings.
>
> **Agent:** Four findings are proposed in the inbox. F-012 supports the handoff hypothesis, backed by six observations. F-013 points to inventory accuracy instead, and two warehouse interviews contradict each other on it. The suspicion is logged as H-004; testing it needs the order-timestamp data, which has not been ingested yet.

The analyst supplied intent, a lens, a hunch and an ambition level. The agent turned the hunch into a hypothesis, surfaced a contradiction, and named the gap in the evidence.

### Skills that draw out the analyst's thinking

Most skills wait for the analyst to supply context. Two skills actively draw it out:

- **`debrief`** — after a meeting, the agent interviews the analyst for about five minutes: what was heard, what was surprising, what was not believed. Answers are recorded as consultant-note observations. This is the most reliable way to capture tacit knowledge before it fades.
- **`challenge`** — the agent argues against a finding or option, using contradicting evidence and past negative lessons. It widens the synthesis and catches blind spots before the client does.

## Cross-engagement learning and confidentiality

Lessons should flow across engagements, but client data must not; the boundary between the two is a deliberate anonymization step.

- **Within an engagement**, everything stays in the engagement folder, including client names and raw sources.
- **Across engagements**, only lessons and option patterns are shared, rewritten to remove client names, figures and identifying details. The consultant approves each lesson before it leaves the engagement.
- **Model use.** Some client contracts restrict sending documents to external AI services. The charter should record what is allowed, and `ingest` should refuse sources marked restricted.
- **Retention.** At close, raw sources follow the client agreement (returned, archived or deleted); anonymized lessons are kept in the firm library.

## Phased build plan

Build in three phases, starting with six core skills tested on a completed engagement whose outcome is already known.

&#91;embedded content: build plan · 3 phases, 2 gates\]
![[Pasted image 20261102120325.png]]
- **Gate 1:** the core loop rebuilds the past engagement's key findings, each with a working evidence trail, and the data model needs no major change.
- **Gate 2:** on a live engagement, triage and synthesis take less time than the current approach, and the what-changed report is used for client updates.
- **After Phase 3:** decide whether a dedicated platform (interface, database, multi-user access) is worth building, based on where the file-based version strains.

## Open questions

- [x] What does a typical engagement look like: length, number of sources, solo or team?
 - 4 weeks, 10-20 sources, team of 1-3 analysts, plus the consultant and client stakeholders. 
- [x] Which deliverables are produced most often, and which should `draft-deliverable` target first?
 - Findings reports, option decks, and a one-page executive summary are the most common. The first target should be the findings report, as it is central to the engagement and informs other deliverables.
- [x] Which client agreements restrict sending documents to an LLM, and what is the fallback for restricted sources?
 - This is project dependent. The fallback is to mark restricted sources in the charter and have the `ingest` skill skip them, while still allowing the rest of the engagement to proceed.
- [ ] Where does synthesis break down most today: finding information, connecting it, or explaining it?
 - unknown; needs observation on a live engagement to answer.
- [x] Should observations be one file each, or grouped per source, at real engagement volumes?
 - Can be grouped in arbitrary ways, but one file per observation is preferred for traceability and versioning. Grouping per source may be acceptable for very large sources, but it risks losing granularity.
- [x] Which editor will be the main working view (Obsidian, VS Code, or another)?
 - VS Code is preferred for its flexibility, but Obsidian may be used for its graph view and markdown support. The choice may depend on the analyst's comfort and the team's workflow.
- [x] Which completed engagement is the best candidate for the Phase 1 trial?
 - Playr1 was a recent engagement with a clear outcome and a manageable number of sources. It is well-documented and has a variety of source types, making it suitable for testing the framework's capabilities.
