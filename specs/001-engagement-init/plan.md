# Implementation Plan: Engagement Initialization

**Branch**: `001-engagement-init` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-engagement-init/spec.md`

## Summary

Provide a `cairn` command with two subcommands:

- `cairn init` creates a new engagement folder in the canonical layout. It writes the seed
  files (README, engagement record, charter, source index, logs), copies one template per
  object type into `_templates/`, copies the Cairn skills into `.claude/skills/`, and
  sets up a local git repository with an initial commit.
- `cairn refresh` updates only the framework-provided files (templates and skills) in an
  existing engagement to the current framework version.

The command is a small Python package that uses only the standard library. All framework
assets (seed files, master templates, skills) ship inside the package. Writes are tracked
so that a failed run removes only what that run created. Safety checks run before
anything is written: no engagement inside the framework repo, no engagement inside
another engagement, no writing into a non-empty folder unless asked, a writable target,
and a complete set of assets. A hidden manifest records a hash for each framework file, so
refresh can tell which ones the consultant has edited.

## Technical Context

**Language/Version**: Python 3.11+ (needed for `tomllib`; developer machines run 3.14)

**Primary Dependencies**: None at runtime (standard library only: `argparse`, `pathlib`,
`importlib.resources`, `hashlib`, `string.Template`, `subprocess`, `unicodedata`,
`tomllib`). `git` CLI is used for version control unless `--no-git` is given. Dev only:
`pytest`, `PyYAML` (for independent front-matter validation in tests), `hatchling` (build).

**Storage**: Plain files in the engagement folder: markdown with YAML front matter, plus
one JSON manifest in `.cairn/` used only by the tool (see research R8)

**Testing**: `pytest` with `tmp_path` fixtures; unit tests for pure helpers, integration
tests that run the CLI as a subprocess against synthetic engagements

**Target Platform**: macOS and Linux consultant workstations

**Project Type**: CLI tool plus bundled framework assets (templates, seed files, skills)

**Performance Goals**: `init` and `refresh` each finish in under 2 s on local disk.
SC-001 (under 2 minutes) mostly depends on how fast the consultant answers the prompts.

**Constraints**: Offline only, with no network calls and no git remote (FR-018). Never
touches `10-sources/raw/` content (FR-014). All-or-nothing writes (FR-017). Copies files
and never symlinks them, so skills stay at the engagement's version.

**Scale/Scope**: 16 folders, 12 seed files, 12 templates and up to 16 skills per
engagement. Teams of 1–3 analysts plus the lead consultant.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / rule | How this plan complies | Status |
|---|---|---|
| I. Text-first | Every content file the tool creates is markdown with YAML front matter, and markdown is the preferred format for all engagement content (FR-009). The script is justified because creating folders, copying files and comparing hashes are deterministic tasks. There is no database or server. `.cairn/manifest.json` is tool bookkeeping that can be rebuilt, not a system of record for engagement content (R8). | Pass |
| II. Originals immutable | `init` only creates `10-sources/raw/` if it is missing, and adds a `.gitkeep` only to a raw folder it created itself. In merge mode it never writes into an existing `raw/`. `refresh` never reads or writes outside `_templates/`, the Cairn skills, `.cairn/` and the `framework_version` line. | Pass |
| III. Atomic, cited evidence | Templates carry `source` + `locator` (observation) and `supported_by` / `contradicted_by` (finding, issue, opportunity, option, hypothesis). Findings link directly to supporting and contradicting observations. Issues and opportunities link to findings, so they link down to observations through those findings, and their contradicting observations are the ones the linked findings list. Linking through findings counts as meeting Principle III (decided 2026-11-03). No objects are created. | Pass |
| IV. Provenance | Every template has `origin`, `confidence`, `confidence_reason` and `inference_confirmed`, which the consultant sets to `true` after checking an `llm-inference` item against a source. The `derived` flag is on source and observation. | Pass |
| V. Stable IDs | Templates use ID placeholders only, and no numbered object is created, so the first ID of each type is `-001` (FR-007). Links are ID lists. | Pass |
| VI. Never delete, supersede | `60-log/changelog.md` is seeded. Refresh backs up edited files before replacing them and never deletes consultant content. | Pass |
| VII. Agents propose (NON-NEGOTIABLE) | Every template defaults to `status: proposed`, `audience: internal`. The tool never sets `active` or `client-ready`. | Pass |
| VIII. Confidentiality (NON-NEGOTIABLE) | Refuses targets inside the framework repo or inside another engagement. Makes no network calls and adds no remote, and warns if the target sits inside an existing repo that has a remote. Model-use policy defaults to `unconfirmed` and is flagged in the README and summary. Supports a code name. Tests use only synthetic engagements. | Pass |
| Canonical layout | Creates exactly the constitution's folders. Hidden tool folders (`.git/`, `.claude/`, `.cairn/`) are outside the content layout. FR-004 covers content folders only (R9). | Pass |
| Skill Contract | No skill is built here. Skills are copied as they are. | N/A |
| Workflow: spec-driven, minimal | Spec exists. Stdlib only, two subcommands, no extra commands (`check` and `dry-run` deferred). | Pass |
| Workflow: validation on known outcomes | Applies to analysis skills. This feature does no analysis. It is validated with synthetic fixtures and the layout check (SC-002). | N/A |

**Post-design re-check (after Phase 1)**: Still passes. The design adds no folders to the
content layout, no runtime dependencies and no network access. The data model keeps every
standard field from FR-006.

## Project Structure

### Documentation (this feature)

```text
specs/001-engagement-init/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R20
├── data-model.md        # Phase 1: engagement record, templates, seed files, manifest
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── cli.md                 # `cairn init` / `cairn refresh` command contract
│   ├── engagement-record.md   # engagement.md schema (read by later skills)
│   └── framework-manifest.md  # .cairn/manifest.json schema and refresh rules
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
pyproject.toml                 # package "cairn", console script `cairn`, dev extras
src/cairn/
├── __init__.py                # __version__ (single source of framework version)
├── __main__.py                # `python3 -m cairn`
├── cli.py                     # argparse, interactive prompts, summary output
├── init_cmd.py                # init workflow: resolve inputs → checks → write → git
├── refresh_cmd.py             # refresh workflow: compare, confirm, back up, replace
├── layout.py                  # canonical folders, seed/template lists, check_layout()
├── safety.py                  # framework-repo, nested, non-empty, permission, asset checks
├── transaction.py             # records created paths; rollback in reverse order
├── gitutil.py                 # git preflight, init, initial commit, remote detection
├── textutil.py                # slugify, flat front-matter reader, yaml-safe quoting, sha256
├── report.py                  # CairnError / UsageError and the run Report (data-model §7)
└── assets/
    ├── seed/                  # README.md, engagement.md, 00-charter/*, 10-sources/index.md, 60-log/*
    ├── templates/             # 12 master templates, one per object type
    └── skills/                # Cairn skills (empty until Phase 1 skill features land)

tests/
├── conftest.py                # run_cairn() subprocess helper, tree_hash(), synthetic names
├── unit/                      # test_textutil.py, test_layout.py, test_safety.py, test_transaction.py
└── integration/               # test_init.py, test_init_safety.py, test_init_merge.py,
                               # test_git.py, test_refresh.py
```

**Structure Decision**: A single Python package in `src/` layout, with the framework
assets stored as package data, so the installed `cairn` command can find them wherever it
runs (R2, R4). Later Phase 1 features add each skill under `src/cairn/assets/skills/<name>/`.
`report.py` holds the shared errors and run report so the command modules don't import each
other. `layout.py` honors two test-only environment variables, `CAIRN_ASSETS_DIR` and
`CAIRN_FRAMEWORK_VERSION`, so integration tests can run against a fixture framework (R19).

## Complexity Tracking

No constitution violations. Nothing to justify.

## Clarifications Applied (2026-11-03)

- **`charter` is out of scope.** US3 and SC-005 are checked with a synthetic test skill
  (R20). `charter` is confirmed when its own feature adds `assets/skills/charter/`.
- **The real client name is optional when a code name is given.** If it's left out, it
  appears nowhere in the generated files. If it's given, it appears only in
  `engagement.md` (data-model §2, contracts/engagement-record.md).
- **Inside an existing repo, the tool neither runs `git init` nor commits.** It warns if
  that repo has a remote (R14, unchanged).
- **Edited skills get the same protection as edited templates during refresh** (R17,
  unchanged).

## Decisions from Analysis (2026-11-03)

- **Principle III is met by linking through findings.** Issues and opportunities cite
  findings, and findings cite observations (Constitution Check, row III).
- **FR-009 covers content files only.** Markdown is preferred for all engagement content.
  `.cairn/`, git files, `.gitkeep` placeholders and copied skill files are exempt.
- **FR-004 covers content folders only.** `.claude/`, `.cairn/` and `.git/` are tool
  folders (R9).
- **New standard field `inference_confirmed`** (default `false`) records that the consultant
  checked an `llm-inference` item against a source (Principle IV, data-model §3.1).
- **Refresh never deletes backups**, even when it fails and restores the original files
  (contracts/framework-manifest.md → Guarantees).
- **The README lists skills as of creation** and points to `.claude/skills/` for the
  current set, because refresh doesn't touch the README (FR-023).
