# Data Model: Engagement Initialization

This feature creates the containers and templates for the Cairn data model. It does not
create any objects. Field names set here are the contract that every later skill
uses (constitution: "a change to the data model MUST update every template and skill
that uses it").

## 1. Engagement

One client project, stored as one folder.

| Attribute | Rule |
|---|---|
| Folder name / `id` | `slugify(code_name or client) + "-" + slugify(engagement_name)` unless a folder is given explicitly (research R15) |
| Location | Chosen by the consultant. Defaults to `./<id>`. Never inside the framework repo or another engagement (R11, R12). |
| Content folders | Exactly the canonical layout (§5) |
| Tool folders | `.claude/skills/`, `.cairn/`, `.git/` (R9) |

**Lifecycle**

~~~text
(none) --cairn init--> created(framework_version = V)
created(V) --cairn refresh, running version W >= V--> created(W)
created(V) --cairn refresh, running version W < V--> refused (no change)
~~~

Close-out (archiving or removing raw sources) is out of scope.

## 2. Engagement record (`engagement.md`)

The full schema is in [contracts/engagement-record.md](contracts/engagement-record.md).
Summary:

| Field | Type | Required | Default | Source |
|---|---|---|---|---|
| `id` | string | yes | derived folder name | R15 |
| `type` | `engagement` | yes | `engagement` | fixed |
| `engagement_name` | string | yes | — | `--engagement` or prompt |
| `client` | string | one of `client` / `client_code_name` | `""` | `--client` or prompt |
| `client_code_name` | string | one of `client` / `client_code_name` | `""` | `--code-name` or prompt |
| `lead_consultant` | string | yes | `git config user.name`, else `$USER` | `--lead` or prompt |
| `team` | list of strings | no | `[]` | `--team` (repeatable) |
| `start_date` | date `YYYY-MM-DD` | yes | today | `--start-date` |
| `created` | date | yes | today | fixed |
| `framework_version` | semver string | yes | running `cairn.__version__` | fixed. Refresh updates it. |
| `model_use` | `allowed` \| `restricted` \| `unconfirmed` | yes | `unconfirmed` | `--model-use` or prompt |
| `model_use_notes` | string: specific restrictions, in the consultant's words | no | `""` | consultant, or the `charter` skill (added in framework 0.2.0) |

**Validation**: `model_use` must be one of the three values (FR-015). `start_date` must be
an ISO date. At least one of `client` and `client_code_name` is non-empty. When
`client_code_name` is set:
- `client` is optional and defaults to `""` (FR-016).
- If `client` is given, it appears **only** in `engagement.md`. The README, the other seed
  files, the summary and the git commit message all use `client_code_name`.
- If `client` is omitted, the real name appears in no generated file.
- Neither `id` nor the folder name may contain `slugify(client)` unless the consultant
  gives a folder explicitly.

Tests check this by searching the whole engagement tree, and the git commit message, for
the real name.

## 3. Object templates (`_templates/`)

There are twelve templates, one per object type (FR-006). They are copied byte for byte
from `src/cairn/assets/templates/`.

### 3.1 Standard fields (every template)

| Field | Values | Template default |
|---|---|---|
| `id` | `<PREFIX>-###` | `"<PREFIX>-###"` placeholder |
| `type` | the object type | the type |
| `title` | short text | `""` |
| `status` | `proposed` \| `active` \| `superseded` \| `rejected` | `proposed` |
| `origin` | `client-document` \| `interview-meeting` \| `external-research` \| `prior-engagement` \| `llm-inference` \| `consultant-note` | `""` |
| `confidence` | `high` \| `medium` \| `low` | `""` |
| `confidence_reason` | one line | `""` |
| `inference_confirmed` | `true` \| `false`. Only the consultant sets `true`, after checking an `origin: llm-inference` item against a source (Principle IV). It is ignored for other origins. | `false` |
| `audience` | `internal` \| `client-ready` | `internal` |
| `supports` | list of IDs | `[]` |
| `contradicts` | list of IDs | `[]` |
| `derived_from` | list of IDs | `[]` |
| `supersedes` | list of IDs | `[]` |
| `clarifies` | list of IDs | `[]` |
| `change_reason` | one line: the reason for the latest supersede or reject (added in 0.2.0; treated as `""` when missing) | `""` |
| `change_trigger` | `new-evidence` \| `client-feedback` \| `rethinking` (added in 0.2.0; treated as `""` when missing) | `""` |
| `created` | `YYYY-MM-DD` | `"YYYY-MM-DD"` placeholder |

Allowed values are written as YAML comments next to each field, so someone editing a file
by hand can see them without other documentation.

### 3.2 Types, prefixes, form and extra fields

| Type | Prefix | Form (R16) | Lives in | Extra fields |
|---|---|---|---|---|
| source | `S` | file | `10-sources/extracted/` | `source_type` (pdf/deck/spreadsheet/image/transcript/web/other), `raw_file` (name in `raw/`), `provided_by`, `source_date`, `extraction_method` (text/ocr/vision-description/mixed), `derived` (bool), `restricted` (bool), `uncertain_passages` (list of locators) |
| observation | `O` | file | `_inbox/` → `30-observations/` | `source` (S-ID), `locator`, `questions` (Q-IDs), `derived` (bool) |
| question | `Q` | entry | `00-charter/questions.md` | `priority` (high/medium/low), `raised_by`, `hypotheses` (H-IDs) |
| hypothesis | `H` | entry | `00-charter/hypotheses.md` | `question` (Q-ID), `confirm_if`, `reject_if` (evidence that would confirm or reject it; added in 0.2.0), `supported_by`, `contradicted_by` (O/F-IDs) |
| assumption | `A` | entry | `00-charter/assumptions.md` | `basis`, `questions` (Q-IDs) |
| research | `R` | file | `20-research/` | `question` (Q- or H-ID), `research_type` (external/prior-art), `citations` (list of URL or reference + locator) |
| finding | `F` | file | `_inbox/` → `40-synthesis/findings/` | `so_what` (one sentence), `supported_by`, `contradicted_by` (O-IDs), `questions` |
| issue | `I` | file | `40-synthesis/issues/` | `supported_by`, `contradicted_by` (F-IDs) |
| opportunity | `P` | file | `40-synthesis/opportunities/` | `supported_by`, `contradicted_by` (F-IDs) |
| option | `X` | file | `_inbox/` → `50-options/` | `addresses` (I/P-IDs), `supported_by`, `contradicted_by`, `lessons_checked` (L-IDs) |
| decision | `D` | entry | `60-log/decisions.md` | `decides` (X/H-IDs), `outcome` (accepted/rejected/deferred), `rationale`, `decided_by`, `decided_on` |
| lesson | `L` | entry | `60-log/lessons.md` | `polarity` (positive/negative), `learned_from` (D/X/H-IDs), `anonymized` (bool), `share_approved` (bool) |

**Naming**: the spec's "research result" is the `research` type. There is no separate
"recommendation" type: a recommendation is an option the consultant accepted, recorded by a
decision (`D-###`) with `outcome: accepted`. Constitution Principle III's linking rule for
recommendations therefore applies to options.

**File-form template**: YAML front matter with the standard and extra fields, then body
headings for the type (for example, an observation's body is the single claim, and a
finding has `## So what`, `## Evidence`, `## Contradicting evidence`).

**Entry-form template**: `## <PREFIX>-###: <title>`, then a fenced `yaml` block with the
standard and extra fields, then free text.

**Validation (tested)**: every template parses (front matter, or the fenced block for
entries), contains every standard field, and has `status: proposed` and
`audience: internal`. No template contains a real ID (`-\d{3}`).

**Object status transitions** (enforced by later skills, not this feature):

~~~text
proposed --consultant--> active --consultant--> superseded | rejected
proposed --consultant--> rejected
audience: internal --consultant only--> client-ready   (never when origin = llm-inference and inference_confirmed = false)
~~~

## 4. Seed files

Seed files are rendered from `src/cairn/assets/seed/` (R5). They contain headings,
guidance and front matter, and no objects (FR-005).

| Path | Front matter | Body |
|---|---|---|
| `README.md` | none | Engagement name, layout table, status and provenance rules, ID prefixes (examples written as `O-###`, never a real number), the daily triage habit, skills available **as of creation** (generated from the copied skills, or "none installed yet"), followed by a note that `.claude/skills/` holds the current set and that `cairn refresh` may add skills not listed here, and a **model-use warning block** when `model_use: unconfirmed` (FR-011, FR-015) |
| `engagement.md` | engagement record (§2) | One line explaining each field, including `model_use_notes` (0.2.0) |
| `00-charter/scope.md` | `type: charter-scope`, `model_use`; from 0.2.0 also `model_use_notes`, `charter_status` (`draft` \| `approved`), `approved_on`, `approved_by` | Objectives, Boundaries (from 0.2.0 with `### In scope` and `### Out of scope`), Deliverables, Timeline, Constraints (0.2.0), **Model use** (`Current policy:` and, from 0.2.0, `Restrictions:` lines; says `engagement.md` is authoritative) |
| `00-charter/questions.md` | `type: collection`, `holds: question` | Guidance + "No questions yet" |
| `00-charter/hypotheses.md` | `type: collection`, `holds: hypothesis` | same |
| `00-charter/assumptions.md` | `type: collection`, `holds: assumption` | same |
| `00-charter/stakeholders.md` | `type: charter-stakeholders` | Table header: name, role, perspective, interview status |
| `00-charter/lenses.md` | `type: charter-lenses` | Guidance + empty Lenses and Evaluation criteria sections |
| `10-sources/index.md` | `type: source-index` | Table header: ID, title, type, date, origin, status, restricted |
| `60-log/decisions.md` | `type: collection`, `holds: decision` | Guidance |
| `60-log/lessons.md` | `type: collection`, `holds: lesson` | Guidance, plus a note on anonymizing before sharing |
| `60-log/changelog.md` | `type: changelog` | Entry format: date, subject, event, reason, trigger, with an optional `> ` detail block. From 0.2.0 the guidance follows the shared change convention (002 `contracts/change-convention.md`): events `supersede`, `correct`, `clarify`, `reject`, `relink`, `scope-change`, `model-use`, `approve-charter` |

## 5. Canonical layout

`layout.py` defines this list once. `init`, the safety checks and `check_layout()` all use it.

~~~text
_inbox/  _templates/  00-charter/  10-sources/  10-sources/raw/  10-sources/extracted/
20-research/  30-observations/  40-synthesis/  40-synthesis/findings/
40-synthesis/issues/  40-synthesis/opportunities/  50-options/  60-log/  70-views/
80-deliverables/
~~~

**Protected areas** (refresh never touches them, FR-023): everything except `_templates/`,
the `.claude/skills/<name>/` folders listed in the manifest, `.cairn/`, and the
`framework_version:` line of `engagement.md`.

## 6. Framework manifest (`.cairn/manifest.json`)

The schema and refresh decision table are in
[contracts/framework-manifest.md](contracts/framework-manifest.md).

| Field | Type | Meaning |
|---|---|---|
| `schema` | int | Manifest format version (`1`) |
| `framework_version` | semver | Version that last wrote the framework files |
| `written` | ISO datetime | When the manifest was last written |
| `files` | map of path → `sha256:<hex>` | Path relative to the engagement root, and the hash of the bytes written |

## 7. Run report (in memory)

Both commands build a report and print it as the summary.

| Field | Meaning |
|---|---|
| `created` | Paths created this run |
| `skipped` | Paths that already existed (merge mode) |
| `updated` / `added` / `removed` / `kept_edited` / `backed_up` | Refresh results |
| `warnings` | Model-use unconfirmed, enclosing repo has a remote, git skipped |
| `next_steps` | Set model-use policy, run `charter`, add originals to `10-sources/raw/` (FR-010) |
