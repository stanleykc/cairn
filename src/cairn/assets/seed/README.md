# ${engagement_name} (${client_display})
${model_use_warning}
This folder holds everything for one engagement: the charter, the original sources, the
evidence extracted from them, the analysis built on that evidence, and the deliverables.
Every file is plain markdown with YAML front matter, so it works in any editor and any
agent can read and write it. The engagement settings (names, dates, model-use policy) are
in `engagement.md`.

## Where things go

| Folder | What goes in it |
|---|---|
| `_inbox/` | **Agent output awaiting your review.** Nothing here counts until you accept it. |
| `_templates/` | One template per object type. Copy one to create a new object. |
| `00-charter/` | Scope, key questions, hypotheses, assumptions, stakeholders and analysis lenses |
| `10-sources/` | The source catalogue (`index.md`) |
| `10-sources/raw/` | **Original files (PDF, PPTX, XLSX, images, audio). Put new originals here. They are never modified.** |
| `10-sources/extracted/` | One markdown file per source (`S-###`), with metadata. All work happens on these. |
| `20-research/` | External and prior-work research (`R-###`), each tied to a question |
| `30-observations/` | Atomic, cited statements (`O-###`): one claim, one source, no interpretation |
| `40-synthesis/` | Analysis built on the observations |
| `40-synthesis/findings/` | Insights and implications (`F-###`) |
| `40-synthesis/issues/` | Problems to solve (`I-###`) |
| `40-synthesis/opportunities/` | Advantages to exploit (`P-###`) |
| `50-options/` | Solutions, tools and enablers (`X-###`), including rejected ones |
| `60-log/` | Decisions (`D-###`), lessons (`L-###`) and the changelog |
| `70-views/` | Generated views: evidence map, what-changed reports |
| `80-deliverables/` | Client-facing drafts and released versions |

In short: **originals go in `10-sources/raw/`**, and **agent output waiting for review is
in `_inbox/`**.

## Status rules

Status lives in front matter, never in the folder a file sits in.

- Every new object starts as `status: proposed` and `audience: internal`.
- `proposed` → `active` → `superseded` or `rejected`. A proposed item can also go straight
  to `rejected`.
- Only the consultant sets an item to `active` or marks it `audience: client-ready`.
  Agents only propose.
- Nothing is deleted. A changed idea is marked `superseded` or `rejected` with a reason,
  and the event is recorded in `60-log/changelog.md`.

## Provenance rules

- Every object records `origin`: `client-document`, `interview-meeting`,
  `external-research`, `prior-engagement`, `llm-inference` or `consultant-note`.
- Every object records `confidence` (`high`, `medium` or `low`) with a one-line
  `confidence_reason`.
- Content derived rather than read verbatim (OCR text, descriptions of charts or photos)
  is flagged `derived: true`.
- Anything a model inferred rather than read has `origin: llm-inference`. It stays
  internal until the consultant checks it against a source and sets
  `inference_confirmed: true`. Only then can it become client-ready.
- Every claim cites a source ID and a locator (page, slide, table, timestamp or URL).

## IDs and links

Every object has a short, permanent ID with a type prefix and the next free number for
that type. IDs are never reused.

| Prefix | Type | Prefix | Type |
|---|---|---|---|
| `S-###` | source | `F-###` | finding |
| `O-###` | observation | `I-###` | issue |
| `Q-###` | question | `P-###` | opportunity |
| `H-###` | hypothesis | `X-###` | option |
| `A-###` | assumption | `D-###` | decision |
| `R-###` | research | `L-###` | lesson |

Link objects by ID only (for example `supported_by: [O-###]`), never by file name or
title, so files can be renamed or moved without breaking links.

## Daily triage

Spend about 15 minutes a day on `_inbox/`. For each item, **accept** it (move it to its
folder and set it `active` once it is cited), **edit** it, **reject** it (with a reason),
or **defer** it. Keep the inbox short; the analysis only moves forward on accepted items.

## Skills available

Skills installed when this engagement was created:

${skills_list}

The current set is in `.claude/skills/`. `cairn refresh` may add skills that are not listed here.

## Keeping the framework up to date

Templates and skills come from the Cairn framework, version ${framework_version} when this
engagement was created. To pick up newer templates and skills, run `cairn refresh` in this
folder. It never touches sources, charter, objects, logs, views, deliverables or the inbox,
and it asks before replacing any template or skill you have edited.
