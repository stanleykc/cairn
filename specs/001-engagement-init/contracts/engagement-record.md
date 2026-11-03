# Contract: Engagement record (`engagement.md`)

`engagement.md` sits at the root of every engagement folder. Its YAML front matter
identifies the engagement and holds settings that later skills read. Skills MUST treat
this file as the authoritative copy of `model_use`. The copy in `00-charter/scope.md` is
there for people to read.

## Front matter

~~~yaml
---
id: "acme-fulfillment-review"        # folder name; never changes after init
type: engagement                     # fixed; used to detect engagements
engagement_name: "Fulfillment Review"
client: "Acme"                       # real name; may be "" when only a code name is used
client_code_name: ""                 # when set, used for id and folder name instead of client
lead_consultant: "Jane Analyst"
team: []                             # e.g. ["Sam Analyst", "Lee Analyst"]
start_date: 2026-11-03
created: 2026-11-03
framework_version: "0.1.0"           # updated only by `cairn refresh`
model_use: unconfirmed               # allowed | restricted | unconfirmed
---
~~~

| Field | Type | Writer | Readers |
|---|---|---|---|
| `id` | string | init | all skills (labels, reports) |
| `type` | `engagement` | init | `cairn` (nested and refresh checks) |
| `engagement_name`, `client`, `client_code_name` | string | init, consultant | `charter`, `draft-deliverable` |
| `lead_consultant`, `team` | string, list | init, consultant | `charter`, `debrief` |
| `start_date`, `created` | ISO date | init | `what-changed` |
| `framework_version` | semver string | init, refresh | `cairn refresh` |
| `model_use` | enum | init, consultant, `charter` | `ingest` (must refuse restricted sources; must warn when `unconfirmed`) |

## Rules

- All string values are written as double-quoted YAML scalars, so names containing `:`,
  `#` or quotes stay valid (R5).
- At least one of `client` and `client_code_name` is non-empty.
- When `client_code_name` is set, this file is the only generated file that may contain
  the real `client` name. Later skills MUST use `client_code_name` in anything they write
  unless the consultant asks otherwise (FR-016).
- `model_use` values mean:
  - `allowed`: the client agreement permits sending source content to external AI services.
  - `restricted`: some or all sources must not be sent. The flag is set per source with
    `restricted: true`.
  - `unconfirmed`: not known yet. Skills MUST treat this as "ask before sending".
- Refresh changes only the `framework_version:` line, and only by replacing that one line.
  Consultants may edit every other field by hand.

## Body

A short explanation of each field, and a reminder that the policy must be confirmed before
ingestion. The body isn't parsed by any tool.
