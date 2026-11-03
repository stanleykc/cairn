---

description: "Task list for Engagement Initialization (cairn init / cairn refresh)"
---

# Tasks: Engagement Initialization

**Input**: Design documents from `/specs/001-engagement-init/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R20), data-model.md, contracts/ (cli.md,
engagement-record.md, framework-manifest.md), quickstart.md

**Tests**: Included. The plan (Testing, R19) and the success criteria (SC-002 "automated layout
check", SC-004 "comparing file contents") call for a `pytest` suite with unit and integration
tests. Integration tests run `python3 -m cairn` as a subprocess in `tmp_path`.

**Organization**: Tasks are grouped by user story so each story can be built and tested on
its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Every task names the exact file(s) it touches

## Path Conventions

Single Python package in `src/` layout (plan.md → Project Structure):
`pyproject.toml`, `src/cairn/`, `src/cairn/assets/{seed,templates,skills}/`,
`tests/{unit,integration}/`.

## Shared Design Decisions (read before starting)

These fill small gaps the plan leaves open. Every task below assumes them.

1. **Module API** (names used across tasks):
   - `cairn.report`: `CairnError(message, hint=None, exit_code=1)`, `UsageError(CairnError)`
     with `exit_code=2`, and `Report` dataclass (data-model §7). This one module is added to
     the plan's structure so `init_cmd`, `refresh_cmd`, `safety`, `gitutil` and `cli` can
     share errors and the report without circular imports.
   - `cairn.textutil`: `slugify(s)`, `yaml_str(s)`, `read_front_matter(text)`, `sha256_bytes(b)`.
   - `cairn.layout`: `CANONICAL_FOLDERS`, `SEED_FILES`, `TEMPLATES`, `MANIFEST_PATH`,
     `assets_root()`, `framework_version()`, `parse_version()`, `missing_assets()`,
     `framework_files()`, `build_manifest()`, `read_manifest()`, `check_layout()`.
   - `cairn.transaction`: `Transaction`.
   - `cairn.gitutil`: `preflight()`, `inside_work_tree()`, `has_remote()`, `init_and_commit()`.
   - `cairn.safety`: `run_init_checks()` plus one function per check.
   - `cairn.init_cmd`: `InitOptions` dataclass, `run(opts) -> Report`.
   - `cairn.refresh_cmd`: `run(path, *, replace_edited, confirm) -> Report`.
   - `cairn.cli`: `main(argv=None) -> int`.
2. **Test hooks for a fixture framework** (needed by R19/R20 and quickstart §8, which run the
   CLI as a subprocess against a temporary copy of the assets at a different version):
   `layout.assets_root()` returns `Path(os.environ["CAIRN_ASSETS_DIR"])` when that variable is
   set, else `importlib.resources.files("cairn") / "assets"`. `layout.framework_version()`
   returns `os.environ["CAIRN_FRAMEWORK_VERSION"]` when set, else `cairn.__version__`.
   Document both in the `layout.py` module docstring as test-only hooks. No other code reads
   the environment for these.
3. **Seed rendering** (R5): seed files are `string.Template` files rendered with
   `substitute()`. Literal `$` in a seed body must be written `$$`. Placeholders available to
   every seed: `${id}`, `${engagement_name}`, `${client_display}` (code name if set, else
   client), `${lead_consultant}`, `${start_date}`, `${created}`, `${framework_version}`,
   `${model_use}`, plus front-matter-safe quoted versions `${id_q}`, `${engagement_name_q}`,
   `${client_q}`, `${client_code_name_q}`, `${lead_consultant_q}`, `${framework_version_q}`
   (each is `yaml_str(value)`), `${team_json}` (`json.dumps(team)`), and README-only
   `${model_use_warning}` and `${skills_list}`. Only `engagement.md` may use `${client_q}`
   (FR-016).
4. **Run everything in `.venv`**: from T014 on, every `python3`, `pytest` and `cairn` command
   runs with `.venv` activated (`source .venv/bin/activate`).
5. **No real IDs anywhere**: templates, seeds and README write IDs as `O-###`, `F-###` etc.,
   never with digits, so `\b[SOQHARFIPXDL]-[0-9]{3}\b` matches nothing in a fresh engagement
   outside `README.md` and `engagement.md`, the two files that hold consultant-typed names
   (FR-007).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package skeleton, build config and dev tooling

- [X] T001 Create the folder skeleton: `src/cairn/`, `src/cairn/assets/seed/00-charter/`, `src/cairn/assets/seed/10-sources/`, `src/cairn/assets/seed/60-log/`, `src/cairn/assets/templates/`, `src/cairn/assets/skills/`, `tests/unit/`, `tests/integration/`; add an empty `src/cairn/assets/skills/.gitkeep` so git keeps the (intentionally empty, R20) skills folder
- [X] T002 Create `pyproject.toml`: `[build-system]` hatchling; `[project]` `name = "cairn"`, `requires-python = ">=3.11"`, `dynamic = ["version"]`, no runtime `dependencies`; `[project.optional-dependencies] dev = ["pytest", "PyYAML"]`; `[project.scripts] cairn = "cairn.cli:main"`; `[tool.hatch.version] path = "src/cairn/__init__.py"`; `[tool.hatch.build.targets.wheel] packages = ["src/cairn"]` (package data under `assets/` is included automatically, R4); `[tool.pytest.ini_options] testpaths = ["tests"]`. The `[project].name` of `"cairn"` is what R11 uses to detect the framework repo
- [X] T003 [P] Create repo-root `.gitignore` with Python build artifacts only: `__pycache__/`, `*.pyc`, `*.egg-info/`, `build/`, `dist/`, `.pytest_cache/`, `.venv/`. Do NOT ignore anything under `src/cairn/assets/`
- [X] T004 [P] Create `src/cairn/__init__.py` with a one-line module docstring and `__version__ = "0.1.0"` (single source of the framework version, R18), and `src/cairn/__main__.py` containing `from cairn.cli import main` and `raise SystemExit(main())`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pure helpers, layout definitions, rollback and the CLI shell that every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Create `src/cairn/report.py`: `class CairnError(Exception)` with attributes `message`, `hint` (optional) and `exit_code` (default `1`); `class UsageError(CairnError)` with `exit_code = 2`; `@dataclass class Report` with list fields `created`, `skipped`, `updated`, `added`, `removed`, `kept_edited`, `backed_up`, `warnings`, `next_steps` (all `field(default_factory=list)`), plus `engagement_id: str = ""`, `engagement_path: Path | None = None`, `framework_version: str = ""`, `previous_version: str = ""`, `git_status: str = ""` and a `counts: dict[str, int]` for the summary line (data-model §7)
- [X] T006 [P] Create `src/cairn/textutil.py` (stdlib only): `slugify(s)` per R15 (NFKD-normalize with `unicodedata`, drop combining marks, lowercase, replace each run of non-`[a-z0-9]` with one `-`, strip `-` at both ends; `"Société Générale"` → `"societe-generale"`); `yaml_str(s)` returning `json.dumps(s, ensure_ascii=False)` (a valid YAML double-quoted scalar, R5); `read_front_matter(text) -> dict[str, str]` returning top-level `key: value` scalars between the first two `---` lines, with surrounding quotes removed and trailing `# comment` stripped from unquoted values, and `{}` when there is no front matter (R6); `sha256_bytes(b) -> str` returning `"sha256:" + hexdigest`
- [X] T007 [P] Create `src/cairn/transaction.py`: `class Transaction` that records every path it creates, in order. Methods: `mkdir(path)` (creates one folder only if missing and records it; use `parents=False`, callers create parents first), `write_bytes(path, data)` (opens with mode `"xb"` so an existing file is never overwritten, records the path), `mark_git_created(path)` (records a `.git/` folder this run created), `rollback()` (deletes recorded files in reverse order, then removes each recorded folder only if empty, then `shutil.rmtree` the recorded `.git/`; never touches a path it did not record; tolerates already-missing paths). Context manager: `__exit__` calls `rollback()` on any exception including `KeyboardInterrupt`, then re-raises (R13, FR-017)
- [X] T008 Create `src/cairn/layout.py` (depends on T006): module docstring documents the two test hooks (Shared Design Decision 2). Define `CANONICAL_FOLDERS` as the 16 POSIX paths in data-model §5 in parent-before-child order: `_inbox`, `_templates`, `00-charter`, `10-sources`, `10-sources/raw`, `10-sources/extracted`, `20-research`, `30-observations`, `40-synthesis`, `40-synthesis/findings`, `40-synthesis/issues`, `40-synthesis/opportunities`, `50-options`, `60-log`, `70-views`, `80-deliverables`. Define `SEED_FILES` as the 12 engagement-relative paths `README.md`, `engagement.md`, `00-charter/scope.md`, `00-charter/questions.md`, `00-charter/hypotheses.md`, `00-charter/assumptions.md`, `00-charter/stakeholders.md`, `00-charter/lenses.md`, `10-sources/index.md`, `60-log/decisions.md`, `60-log/lessons.md`, `60-log/changelog.md` (each read from `assets/seed/<same path>`). Define `TEMPLATES` as 12 `(type, prefix, filename)` tuples from data-model §3.2: source/S, observation/O, question/Q, hypothesis/H, assumption/A, research/R, finding/F, issue/I, opportunity/P, option/X, decision/D, lesson/L, with filename `<type>.md`. Define `MANIFEST_PATH = ".cairn/manifest.json"`. Implement `assets_root()`, `framework_version()`, `parse_version(s)` (integer tuple, pre-release suffix after `-` or `+` ignored, R18), `missing_assets(root) -> list[str]` (every seed file and all 12 templates must exist), `framework_files(root) -> dict[str, bytes]` (maps `_templates/<file>` to template bytes; skills are added in US3), `build_manifest(files, version) -> dict` (`schema: 1`, `framework_version`, `written` as `datetime.now().isoformat(timespec="seconds")`, `files` sorted path → `sha256_bytes`), `read_manifest(engagement) -> dict` (raises `CairnError` if missing or unparsable), and `check_layout(path, *, fresh=True) -> list[str]` returning problems: missing or extra non-dot folders (compared recursively, dot-folders skipped, R9), missing seed files, `.md` files other than `README.md` whose front matter is empty, and (when `fresh`) any `\b[SOQHARFIPXDL]-\d{3}\b` match in a `.md` outside dot-folders, skipping `README.md` and `engagement.md` because they contain names the consultant typed (a name like "Project X-100" is not an object) (FR-007). An empty list means the layout is correct (SC-002)
- [X] T009 Create `src/cairn/cli.py` shell (depends on T005): `main(argv=None) -> int` builds an `argparse.ArgumentParser(prog="cairn")` with `--version` printing `cairn <framework_version()>`, and `init` and `refresh` subparsers (their options and handlers are added in US1 and US4). Wrap dispatch so `CairnError` prints `cairn: error: <message>` and, if set, `hint: <hint>` to stderr and returns `exit_code`; `KeyboardInterrupt` prints `cairn: interrupted` to stderr and returns `130`; missing subcommand prints help and returns `2` (contracts/cli.md → Exit codes)
- [X] T010 [P] Create `tests/conftest.py` with fixtures/helpers: `git_env(tmp_path)` writes a temp gitconfig with `user.name = Test Lead`, `user.email = test-lead@example.invalid`, `init.defaultBranch = main` and returns an env dict with `GIT_CONFIG_GLOBAL` set to it and `GIT_CONFIG_NOSYSTEM=1`; `run_cairn(*args, cwd, env=None, input=None) -> CompletedProcess` running `[sys.executable, "-m", "cairn", *args]` with `stdin=subprocess.DEVNULL` unless `input` is given, `capture_output=True, text=True`; `tree_hash(path, exclude=()) -> dict[str, str]` mapping each file's relative POSIX path to its SHA-256, skipping excluded prefixes; `fixture_assets(tmp_path, version="0.1.0", skills=None) -> dict` that copies `cairn` package `assets/` to `tmp_path/"assets"`, writes each `skills[name]` as `skills/<name>/SKILL.md`, and returns env additions `CAIRN_ASSETS_DIR` and `CAIRN_FRAMEWORK_VERSION`; constants for synthetic names only (`"Acme"`, `"Globex"`, `"Globex Corporation"`, `"Falcon"`, `"Fulfillment Review"`, `"Pricing Study"`, Principle VIII)
- [X] T011 [P] Create `tests/unit/test_textutil.py`: `slugify` cases (`"Société Générale"` + `"Q4: Fulfillment Review!"` → `societe-generale-q4-fulfillment-review`, all-punctuation → `""`, repeated spaces/hyphens collapse); `yaml_str` output for values containing `:`, `#`, `"` and accents parses back with PyYAML to the original string; `read_front_matter` on quoted, unquoted, commented and missing front matter; `sha256_bytes` prefix and known digest
- [X] T012 [P] Create `tests/unit/test_transaction.py`: rollback after an exception removes created files and folders in reverse order; a pre-existing file and a pre-existing folder survive rollback; `write_bytes` on an existing path raises `FileExistsError` and leaves it unchanged; a folder that gained an unrecorded file is not removed; `KeyboardInterrupt` inside the `with` block triggers rollback and re-raises
- [X] T013 Create `tests/unit/test_layout.py` (depends on T008): `len(CANONICAL_FOLDERS) == 16`, `len(SEED_FILES) == 12`, `len(TEMPLATES) == 12` with unique prefixes; `parse_version("0.2.0") > parse_version("0.1.9")`, `parse_version("1.0.0-rc1") == (1, 0, 0)`; `check_layout` returns `[]` for a hand-built correct tree in `tmp_path` and names the problem for a missing folder, an extra folder, a missing seed file, and a file containing `O-001`; dot-folders (`.git`, `.claude`, `.cairn`) are ignored; `assets_root()` honors `CAIRN_ASSETS_DIR` via `monkeypatch.setenv`
- [X] T014 Install and smoke-test the foundation inside a virtual environment (Homebrew's Python 3.14 is marked externally managed, PEP 668, so a plain `pip install` outside a venv fails): run `python3 -m venv .venv`, `source .venv/bin/activate`, `python3 -m pip install -e '.[dev]'`, then confirm `cairn --version` and `python3 -m cairn --version` print `cairn 0.1.0`, and `python3 -m pytest tests/unit` passes

**Checkpoint**: Foundation ready. User story work can begin.

---

## Phase 3: User Story 1 - Create a new engagement workspace (Priority: P1) 🎯 MVP

**Goal**: `cairn init` creates an engagement folder with the 16 canonical folders, 12 seed files,
12 object templates, a manifest, and a git repo with one initial commit.

**Independent Test**: `cairn init --engagement "Fulfillment Review" --client "Acme" --lead "Test Lead"`
in an empty `tmp_path` creates `acme-fulfillment-review/`; `check_layout()` returns `[]`; every
`.md` front matter parses with PyYAML; `_templates/` has 12 files with `status: proposed` and
`audience: internal`; no real ID exists; `git log` shows one commit and `git remote` is empty.

### Tests for User Story 1

> Write these first and confirm they fail before implementing.

- [X] T015 [P] [US1] Add template asset validation to `tests/unit/test_layout.py`: for each of the 12 files in `src/cairn/assets/templates/`, parse the YAML (front matter for file-form; the first fenced ```` ```yaml ```` block for entry-form `question`, `hypothesis`, `assumption`, `decision`, `lesson`) with PyYAML; assert every standard field from data-model §3.1 is present (`id`, `type`, `title`, `status`, `origin`, `confidence`, `confidence_reason`, `inference_confirmed`, `audience`, `supports`, `contradicts`, `derived_from`, `supersedes`, `clarifies`, `created`), that `status == "proposed"`, `audience == "internal"`, `inference_confirmed is False`, `type` equals the template's type, `id == "<PREFIX>-###"`, every extra field from data-model §3.2 for that type is present, and no `\b[SOQHARFIPXDL]-\d{3}\b` match exists in the file; also assert no such match exists in any unrendered seed file under `src/cairn/assets/seed/` (this covers `README.md` and `engagement.md`, which `check_layout` skips)
- [X] T016 [P] [US1] Create `tests/integration/test_init.py` (uses `run_cairn`, `git_env`): `test_layout` (exit 0, folder `acme-fulfillment-review` created, `check_layout(path) == []`); `test_seed_files` (all 12 present, every `.md` except README parses with PyYAML, collections have `type: collection` and the right `holds`); `test_templates` (12 files in `_templates/`, byte-identical to `src/cairn/assets/templates/`); `test_engagement_record` (front matter has every field in contracts/engagement-record.md with the given values, `type: engagement`, `framework_version: "0.1.0"`, `model_use: unconfirmed`, `team: []`, `created` and `start_date` equal today); `test_no_numbered_objects` (`\b[SOQHARFIPXDL]-[0-9]{3}\b` matches nothing in any `.md`, including `README.md` and `engagement.md`, since the synthetic names contain no ID-like text); `test_manifest` (`.cairn/manifest.json` has `schema: 1` and lists exactly the 12 `_templates/` paths with correct hashes, and no seed files); `test_slug_from_accents` (`--client "Société Générale" --engagement "Q4: Fulfillment Review!"` → `societe-generale-q4-fulfillment-review`, names kept as typed in `engagement.md`); `test_explicit_path` (`cairn init other-name ...` uses `other-name` as `id`); `test_summary` (stdout contains `Created engagement`, `16 folders · 12 seed files · 12 templates · 0 skills`, the `Model-use policy is UNCONFIRMED` line and the three next steps from contracts/cli.md); `test_missing_engagement_non_tty` (exit 2, stderr names `--engagement`, no folder created); `test_prompts` (in-process: monkeypatch `sys.stdin.isatty` → `True` and `builtins.input` with queued answers, call `cli.main(["init", "--no-git"])` with `cwd` = `tmp_path`, assert prompt order engagement → client → lead and the folder is created)
- [X] T017 [P] [US1] Create `tests/integration/test_git.py`: default run → `git log --format=%s` is exactly `Initialize engagement acme-fulfillment-review (cairn 0.1.0)`, one commit, `git remote` empty, `git status --porcelain` empty, `10-sources/raw/.gitkeep` is tracked; `--no-git` → no `.git/`; target inside an existing repo (`git init` a parent in `tmp_path`) → no nested `.git/`, no new commit in the parent, summary says files are uncommitted; same with `git remote add origin https://example.invalid/x.git` in the parent → summary/stderr warns about the remote; missing git identity (empty `GIT_CONFIG_GLOBAL`, `HOME` set to an empty tmp dir) → exit 1, hint mentions `git config` and `--no-git`, nothing created

### Implementation for User Story 1

**Object templates** (T018–T029). Each is copied byte for byte into `_templates/` (no rendering).
Every template starts with this **standard field block**, with each allowed-value list written
as a YAML comment so hand editors see it (data-model §3.1):

~~~yaml
id: "<PREFIX>-###"        # permanent; next free number for this type, never reused
type: <type>
title: ""
status: proposed          # proposed | active | superseded | rejected
origin: ""                # client-document | interview-meeting | external-research | prior-engagement | llm-inference | consultant-note
confidence: ""            # high | medium | low
confidence_reason: ""     # one line
inference_confirmed: false  # consultant sets true after checking an llm-inference item against a source
audience: internal        # internal | client-ready (only the consultant sets client-ready)
supports: []              # IDs
contradicts: []           # IDs
derived_from: []          # IDs
supersedes: []            # IDs
clarifies: []             # IDs
created: "YYYY-MM-DD"
~~~

Extra fields follow, with defaults `""` for strings, `[]` for ID lists and `false` for booleans.
**File-form** templates wrap the fields in `---` front matter and then add body headings.
**Entry-form** templates (R16) are `## <PREFIX>-###: <short title>`, then a fenced `yaml` block
holding the fields, then a free-text line.

- [X] T018 [P] [US1] Create `src/cairn/assets/templates/source.md` (file form, prefix `S`, lives in `10-sources/extracted/`): extra fields `source_type: ""  # pdf | deck | spreadsheet | image | transcript | web | other`, `raw_file: ""  # file name in 10-sources/raw/`, `provided_by: ""`, `source_date: ""`, `extraction_method: ""  # text | ocr | vision-description | mixed`, `derived: false`, `restricted: false`, `uncertain_passages: []  # locators`; body headings `## Summary`, `## Extracted content`, `## Uncertain passages`, with a one-line note that the original in `raw/` is never modified (Principle II)
- [X] T019 [P] [US1] Create `src/cairn/assets/templates/observation.md` (file form, prefix `O`, lives in `_inbox/` → `30-observations/`): extra fields `source: ""  # S-ID`, `locator: ""  # page, slide, table, timestamp or URL`, `questions: []  # Q-IDs`, `derived: false`; body is a single placeholder line `One claim, from one source, with no interpretation.` (Principle III)
- [X] T020 [P] [US1] Create `src/cairn/assets/templates/question.md` (entry form, prefix `Q`, lives in `00-charter/questions.md`): heading `## Q-###: <short title>`; extra fields `priority: ""  # high | medium | low`, `raised_by: ""`, `hypotheses: []  # H-IDs`
- [X] T021 [P] [US1] Create `src/cairn/assets/templates/hypothesis.md` (entry form, prefix `H`, lives in `00-charter/hypotheses.md`): heading `## H-###: <short title>`; extra fields `question: ""  # Q-ID`, `supported_by: []  # O/F-IDs`, `contradicted_by: []  # O/F-IDs`
- [X] T022 [P] [US1] Create `src/cairn/assets/templates/assumption.md` (entry form, prefix `A`, lives in `00-charter/assumptions.md`): heading `## A-###: <short title>`; extra fields `basis: ""`, `questions: []  # Q-IDs`
- [X] T023 [P] [US1] Create `src/cairn/assets/templates/research.md` (file form, prefix `R`, lives in `20-research/`): extra fields `question: ""  # Q- or H-ID`, `research_type: ""  # external | prior-art`, `citations: []  # URL or reference + locator`; body headings `## Question`, `## Results`, `## Citations`
- [X] T024 [P] [US1] Create `src/cairn/assets/templates/finding.md` (file form, prefix `F`, lives in `_inbox/` → `40-synthesis/findings/`): extra fields `so_what: ""  # one sentence`, `supported_by: []  # O-IDs`, `contradicted_by: []  # O-IDs`, `questions: []  # Q-IDs`; body headings `## So what`, `## Evidence`, `## Contradicting evidence`
- [X] T025 [P] [US1] Create `src/cairn/assets/templates/issue.md` (file form, prefix `I`, lives in `40-synthesis/issues/`): extra fields `supported_by: []  # F-IDs`, `contradicted_by: []  # F-IDs`; body headings `## Problem`, `## Evidence`, `## Contradicting evidence`
- [X] T026 [P] [US1] Create `src/cairn/assets/templates/opportunity.md` (file form, prefix `P`, lives in `40-synthesis/opportunities/`): extra fields `supported_by: []  # F-IDs`, `contradicted_by: []  # F-IDs`; body headings `## Opportunity`, `## Evidence`, `## Contradicting evidence`
- [X] T027 [P] [US1] Create `src/cairn/assets/templates/option.md` (file form, prefix `X`, lives in `_inbox/` → `50-options/`): extra fields `addresses: []  # I/P-IDs`, `supported_by: []  # IDs`, `contradicted_by: []  # IDs`, `lessons_checked: []  # L-IDs`; body headings `## Description`, `## Evidence`, `## Contradicting evidence`, `## Lessons checked`, `## Risks`, with a note that rejected options keep their rationale (Principle VI)
- [X] T028 [P] [US1] Create `src/cairn/assets/templates/decision.md` (entry form, prefix `D`, lives in `60-log/decisions.md`): heading `## D-###: <short title>`; extra fields `decides: []  # X/H-IDs`, `outcome: ""  # accepted | rejected | deferred`, `rationale: ""`, `decided_by: ""`, `decided_on: ""  # YYYY-MM-DD`
- [X] T029 [P] [US1] Create `src/cairn/assets/templates/lesson.md` (entry form, prefix `L`, lives in `60-log/lessons.md`): heading `## L-###: <short title>`; extra fields `polarity: ""  # positive | negative`, `learned_from: []  # D/X/H-IDs`, `anonymized: false`, `share_approved: false  # consultant approval required before a lesson leaves the engagement`

**Seed files** (T030–T036). `string.Template` files (Shared Design Decision 3). Headings,
guidance and front matter only; no objects (FR-005).

- [X] T030 [P] [US1] Create `src/cairn/assets/seed/README.md` (no front matter, FR-011): title `# ${engagement_name} (${client_display})`; `${model_use_warning}` placeholder directly under the title; a layout table with one row per canonical folder and its purpose (taken from the "Prototype folder structure" in `requirements-draft/description.md`), stating plainly that originals go in `10-sources/raw/` and are never modified, and that agent output awaiting review lands in `_inbox/` (SC-007); status rules (`proposed` → `active` → `superseded`/`rejected`, only the consultant sets `active` or `client-ready`); provenance rules (`origin`, `confidence` + reason, `derived`, LLM inference never client-ready until confirmed); ID prefixes table S/O/Q/H/A/R/F/I/P/X/D/L written as `O-###` style, link by ID only; the daily triage habit (~15 minutes, accept/edit/reject/defer items in `_inbox/` with a reason for each reject); `## Skills available` with the line `Skills installed when this engagement was created:`, then `${skills_list}`, then the note `The current set is in \`.claude/skills/\`. \`cairn refresh\` may add skills that are not listed here.`; provenance rules must mention `inference_confirmed` (an `llm-inference` item stays internal until the consultant confirms it against a source); a short "Keeping the framework up to date" note pointing to `cairn refresh`
- [X] T031 [P] [US1] Create `src/cairn/assets/seed/engagement.md` per contracts/engagement-record.md: front matter, in order, `id: ${id_q}`, `type: engagement`, `engagement_name: ${engagement_name_q}`, `client: ${client_q}`, `client_code_name: ${client_code_name_q}`, `lead_consultant: ${lead_consultant_q}`, `team: ${team_json}`, `start_date: ${start_date}`, `created: ${created}`, `framework_version: ${framework_version_q}  # updated only by cairn refresh`, `model_use: ${model_use}  # allowed | restricted | unconfirmed`; body with one line explaining each field and a reminder that `model_use` must be confirmed before any source is ingested and that this file is the authoritative copy
- [X] T032 [P] [US1] Create `src/cairn/assets/seed/00-charter/scope.md`: front matter `type: charter-scope` and `model_use: ${model_use}`; body headings `## Objectives`, `## Boundaries`, `## Deliverables`, `## Timeline`, `## Model use` (shows `${model_use}` and says `engagement.md` is authoritative), each with one guidance line (FR-015)
- [X] T033 [P] [US1] Create the three charter collection seeds `src/cairn/assets/seed/00-charter/questions.md`, `hypotheses.md`, `assumptions.md`: front matter `type: collection` and `holds: question` / `hypothesis` / `assumption`; body: one-paragraph guidance (entries use `## Q-###: <title>` + fenced yaml from `_templates/question.md`, etc.; hypotheses link to a question) and the line `No questions yet.` / `No hypotheses yet.` / `No assumptions yet.`
- [X] T034 [P] [US1] Create `src/cairn/assets/seed/00-charter/stakeholders.md` (front matter `type: charter-stakeholders`; table header `| Name | Role | Perspective | Interview status |` with separator row and no data rows) and `src/cairn/assets/seed/00-charter/lenses.md` (front matter `type: charter-lenses`; guidance line plus empty `## Lenses` and `## Evaluation criteria` sections)
- [X] T035 [P] [US1] Create `src/cairn/assets/seed/10-sources/index.md`: front matter `type: source-index`; guidance line (one row per `S-###` in `extracted/`; originals stay in `raw/`); table header `| ID | Title | Type | Date | Origin | Status | Restricted |` with separator row and no data rows
- [X] T036 [P] [US1] Create the log seeds: `src/cairn/assets/seed/60-log/decisions.md` (front matter `type: collection`, `holds: decision`; guidance), `src/cairn/assets/seed/60-log/lessons.md` (front matter `type: collection`, `holds: lesson`; guidance plus a note that lessons must be anonymized and approved by the consultant before sharing outside the engagement, Principle VIII), and `src/cairn/assets/seed/60-log/changelog.md` (front matter `type: changelog`; entry format: date, object ID, event `supersede | clarify | correct`, reason, trigger `new evidence | client feedback | rethinking`)

**Code**

- [X] T037 [US1] Create `src/cairn/gitutil.py` (R14) using `subprocess.run([...], check=False, capture_output=True, text=True)` with no shell: `preflight()` raises `CairnError` with a hint (`git config --global user.name "…"` / `--no-git`) if `shutil.which("git")` is `None` or `git config user.name` / `user.email` is empty; `inside_work_tree(path) -> bool` runs `git rev-parse --is-inside-work-tree` from the nearest existing ancestor of `path`; `has_remote(path) -> bool` (non-empty `git remote` output); `init_and_commit(path, message) -> str` runs `git init`, `git add -A`, `git commit -m message` in `path` and returns the short SHA (`git rev-parse --short HEAD`); raises `CairnError` with git's stderr on any failure. Never runs `git remote add` or any network command (FR-018)
- [X] T038 [US1] Create `src/cairn/init_cmd.py` (depends on T008, T007, T037): `@dataclass InitOptions` (`path: str | None`, `engagement: str`, `client: str = ""`, `code_name: str = ""`, `lead: str`, `team: list[str]`, `start_date: date`, `model_use: str = "unconfirmed"`, `merge: bool = False`, `no_git: bool = False`); `resolve_target(opts) -> tuple[Path, str]` (no path → `cwd / (slugify(code_name or client) + "-" + slugify(engagement))`; given path → `Path(path).resolve()` and `id = slugify(basename)`; empty slug → `UsageError`); `render_seed(rel, values) -> bytes` with `string.Template(...).substitute(values)`; `run(opts) -> Report`: (1) validate inputs; (2) if not `no_git`, call `gitutil.preflight()` and remember `inside_work_tree(target)` — all before any write; (3) open `with Transaction() as tx:` — steps 3a–3g ALL run inside this one block, so any failure, including a failed git step, rolls back everything this run created (R13, FR-017): (3a) create each missing ancestor of the target, top-down, with `tx.mkdir` (supports `cairn init a/b/eng` when `a/` doesn't exist), then the target folder if missing; (3b) each `CANONICAL_FOLDERS` entry; (3c) render each `SEED_FILES` entry; (3d) write each `framework_files()` entry; (3e) write `.cairn/manifest.json` from `build_manifest()` (pretty JSON, sorted keys, trailing newline); (3f) write `.gitkeep` into every canonical folder this run created that is still empty; (3g) git: if `no_git` → report `git: skipped (--no-git)`; if inside an existing work tree → no init, no commit, report the files are uncommitted, and add a warning if `has_remote()`; else call `tx.mark_git_created(target / ".git")` and then `init_and_commit(target, f"Initialize engagement {id} (cairn {version})")`, so a failed `git init` or commit is rolled back too. Fill `Report` (`created`, `counts` for folders/seed files/templates/skills, `git_status`, `warnings` including `Model-use policy is UNCONFIRMED. Set model_use in engagement.md before ingesting any source.` when unconfirmed, and the three `next_steps` from FR-010). In US1, `${model_use_warning}` renders the README warning block when `model_use == "unconfirmed"` and `""` otherwise, and `${skills_list}` renders `None installed yet.`
- [X] T039 [US1] Add the `init` subcommand to `src/cairn/cli.py` (depends on T038): positional `PATH` (optional), `--engagement`, `--client`, `--lead`, `--team` (`action="append"`), `--start-date` (parsed with `date.fromisoformat`, bad value → `UsageError`), `--no-git`. Lead default: `git config user.name`, else `$USER`. For each missing required value: if `sys.stdin.isatty()`, prompt with `input()` in the order engagement name → client name → lead consultant (default shown in brackets); otherwise raise `UsageError` naming the missing flag(s). All prompts happen before `init_cmd.run()`. Print the summary to stdout in the exact shape of contracts/cli.md → Summary (`Created engagement <id> at <path>`, the counts line `framework <v> · <n> folders · <n> seed files · <n> templates · <n> skills`, the git line, any `! ` warnings, `Next steps:` numbered list)
- [X] T040 [US1] Run `python3 -m pytest tests/unit tests/integration/test_init.py tests/integration/test_git.py` and fix failures until green; then run quickstart.md scenarios 1–3 by hand in a `mktemp -d` folder

**Checkpoint**: US1 is fully functional. A consultant can create a correctly laid-out, git-tracked engagement.

---

## Phase 4: User Story 2 - Safe and confidential by default (Priority: P1)

**Goal**: Refuse unsafe targets with nothing written, support merge mode without touching existing
files, record a model-use policy (default `unconfirmed`), keep the real client name out of every
file except `engagement.md`, and roll back completely on failure.

**Independent Test**: Init inside a fake framework repo, inside another engagement, and into a
non-empty folder → exit 1 and `tree_hash` unchanged. Init with `--code-name Falcon --client "Globex
Corporation"` → `Globex` appears only in `engagement.md` and not in the commit message. Init with no
`--model-use` → `unconfirmed` in `engagement.md` and `00-charter/scope.md`.

### Tests for User Story 2

- [X] T041 [P] [US2] Create `tests/unit/test_safety.py`: `check_not_in_framework` refuses a target under a `tmp_path` folder whose `pyproject.toml` has `[project] name = "cairn"`, accepts one whose name is `"other"`, and refuses a (non-existent, nothing written) path under the running package's own project root; `check_not_nested` refuses a target under a folder with `engagement.md` `type: engagement` and under a folder with `.cairn/manifest.json`, and in merge mode refuses a target that is itself an engagement with a hint containing `cairn refresh`; `check_target_empty` refuses a non-empty folder listing at most 10 entries and suggesting `<id>-2`, accepts a missing or empty folder, accepts non-empty with `merge=True`; `check_writable` refuses a read-only parent (skip when `os.geteuid() == 0`); `check_assets` lists each missing seed/template by path
- [X] T042 [P] [US2] Create `tests/integration/test_init_safety.py`: refuse inside a fake framework repo (exit 1, stderr contains `inside the Cairn framework repository`, `tree_hash` of the fake repo unchanged); refuse inside another engagement (`cd` into `acme-fulfillment-review/20-research` → exit 1, `inside another engagement`); second identical run → exit 1, conflict list, `acme-fulfillment-review-2` suggestion; read-only parent → exit 1, `not writable`; missing template via `fixture_assets` with one template deleted → exit 1, the missing path is named, nothing created; `--model-use restricted` recorded in `engagement.md` and `scope.md`; `--model-use bogus` → exit 2; omitted policy → `unconfirmed` in both files, README contains the warning block, summary contains `UNCONFIRMED`; `--model-use allowed` → no warning in README or summary; code name with client (`--client "Globex Corporation" --code-name Falcon`) → folder `falcon-pricing-study`, `id: "falcon-pricing-study"`, `grep -rl Globex` over the tree excluding `.git` returns only `engagement.md`, `git log --format=%B` has no `Globex`, and no entry name under the run's working folder (`work = tmp_path / "work"`, the `cwd` for this run) contains `globex` — check only below `work`, because pytest names `tmp_path` after the test function; code name without client → `client: ""` and `Globex` appears nowhere; rollback fault injection (in-process: monkeypatch `cairn.transaction.Transaction.write_bytes` to raise `OSError` after 5 calls, call `init_cmd.run()`, assert `CairnError`/`OSError` propagates and the target folder is gone and a pre-existing sibling file is untouched); Ctrl-C at the first prompt (in-process, `input` raises `KeyboardInterrupt`) → `cli.main` returns 130 and no folder exists
- [X] T043 [P] [US2] Create `tests/integration/test_init_merge.py` (quickstart §6): pre-create `existing/10-sources/raw/brief.pdf` (`orig`) and `existing/README.md` (`# mine`), take `tree_hash`; run `cairn init existing --merge ...`; assert exit 0, every pre-existing file byte-identical (SC-004), `README.md` and `10-sources/raw/brief.pdf` listed under `Skipped (already present):` in stdout, no `.gitkeep` in the pre-existing `raw/`, all other canonical folders and seed files created; a pre-existing `_templates/finding.md` is skipped AND absent from `.cairn/manifest.json` (so refresh treats it as edited, framework-manifest.md); without `--merge` the same folder is refused with nothing written

### Implementation for User Story 2

- [X] T044 [US2] Create `src/cairn/safety.py` (R11, R12, contracts/cli.md checks 2–6), each function raising `CairnError` with message and hint: `check_not_in_framework(target)` (walk `target` and its ancestors; refuse if any has a `pyproject.toml` whose `tomllib`-parsed `project.name == "cairn"`; also refuse if `target` is inside the project root of the running package, found by walking up from `Path(cairn.__file__)` to the first folder holding such a `pyproject.toml`; message `target is inside the Cairn framework repository`); `check_not_nested(target, merge)` (refuse if any ancestor has `engagement.md` with front-matter `type: engagement` or has `.cairn/manifest.json`, message `target is inside another engagement: <ancestor>`; if `target` itself is an engagement, refuse with hint `use cairn refresh` in merge mode, or as a conflict otherwise); `check_target_empty(target, merge, engagement_id)` (refuse non-empty without merge, listing up to 10 entries, hint suggesting `<id>-2`); `check_writable(target)` (`os.access(..., os.W_OK)` on the target if it exists, else on its nearest existing ancestor, message `not writable: <path>`); `check_assets(root)` (wraps `layout.missing_assets`); `run_init_checks(target, engagement_id, merge)` calling them in contract order. Only reads files; never writes
- [X] T045 [US2] Wire safety and merge into `src/cairn/init_cmd.py` (depends on T044): validate `model_use in {"allowed", "restricted", "unconfirmed"}` (else `UsageError`) and require one of `client`/`code_name`; call `safety.run_init_checks()` after input validation and before git preflight; in merge mode, skip every folder and file that already exists and append it to `report.skipped` (never call `write_bytes` on an existing path), never write anything inside a `10-sources/raw/` that existed before the run, and leave skipped framework files out of the manifest; set `client_display = code_name or client`, `client_q = yaml_str(client)` (empty when omitted), use `client_display` in every non-`engagement.md` value, in the commit message and in the summary (FR-016); compute `${model_use_warning}` from the actual policy; on any exception, let `Transaction` roll back and re-raise as `CairnError("initialization failed: <reason>; removed everything this run created")` (FR-017), letting `KeyboardInterrupt` propagate for exit 130
- [X] T046 [US2] Extend the `init` subcommand in `src/cairn/cli.py`: add `--code-name`, `--model-use` (`choices=["allowed", "restricted", "unconfirmed"]`, default `None` → `unconfirmed`), `--merge`; update the prompt order to exactly contracts/cli.md (1 engagement name, 2 client code name – blank = none, 3 client name – required only if no code name, blank = leave out, 4 lead consultant with default, 5 model-use policy with default `unconfirmed`); non-TTY with neither `--client` nor `--code-name` → `UsageError` naming `--client or --code-name`; print `Skipped (already present):` with one path per line before `Next steps:` when `report.skipped` is non-empty. Then update `test_prompts` in `tests/integration/test_init.py` (from T016) for the new five-prompt order: queue answers engagement, blank code name, client, lead, blank policy, and assert `model_use: unconfirmed`; add a second case with a code name and a blank client
- [X] T047 [US2] Run `python3 -m pytest tests/unit tests/integration` and fix failures until green; then run quickstart.md scenarios 4–6 by hand

**Checkpoint**: US1 and US2 work. Unsafe targets are refused with zero writes; confidentiality defaults hold.

---

## Phase 5: User Story 3 - Agent-ready from the first minute (Priority: P2)

**Goal**: Every skill bundled in `src/cairn/assets/skills/` is copied (never symlinked) into
`<engagement>/.claude/skills/<name>/`, recorded in the manifest, and listed in the README.

**Independent Test**: With `fixture_assets(skills={"demo-skill": ...})`, `cairn init` creates
`.claude/skills/demo-skill/SKILL.md` as a regular file identical to the fixture, the manifest lists
it, the README lists `demo-skill`, and `engagement.md` shows the fixture framework version.

### Tests for User Story 3

- [X] T048 [P] [US3] Add to `tests/integration/test_init.py`: `test_skills_copied` (fixture skill `demo-skill` with `SKILL.md` front matter `name: demo-skill` and `description: "Synthetic test skill"` plus a nested `scripts/check.py`; after init, both files exist under `.claude/skills/demo-skill/`, are regular files (`not is_symlink()`), are byte-identical to the fixture, are listed in `.cairn/manifest.json`, the README `## Skills available` section lists `demo-skill — Synthetic test skill` under `Skills installed when this engagement was created:` and contains the pointer to `.claude/skills/`, and the summary says `1 skills`); `test_no_skills_bundled` (default assets: no `.claude/skills/` entries, `.gitkeep` from the assets folder is not copied, README says `None installed yet.` and still contains the pointer to `.claude/skills/`); `test_framework_version_recorded` (with `CAIRN_FRAMEWORK_VERSION=0.3.0`, `engagement.md` has `framework_version: "0.3.0"` and the manifest `framework_version` is `0.3.0`, US3-2); `test_skills_dir_not_in_layout` (`check_layout` still returns `[]` with `.claude/` present, R9)

### Implementation for User Story 3

- [X] T049 [US3] Extend `framework_files()` and `missing_assets()` in `src/cairn/layout.py` (R10): every sub-folder `<name>` of `assets_root()/"skills"` whose name does not start with `.` is a skill; walk it recursively and map each file to `.claude/skills/<name>/<relative path>`; ignore dot-files directly in `skills/` (e.g. `.gitkeep`); a skill folder without `SKILL.md` is reported by `missing_assets()` as `skills/<name>/SKILL.md`. Add `bundled_skills(root) -> list[tuple[str, str]]` returning `(name, description)` read from each `SKILL.md` with `read_front_matter` (description `""` if absent)
- [X] T050 [US3] Update `src/cairn/init_cmd.py`: create `.claude/` and `.claude/skills/<name>/...` parent folders through the `Transaction` before writing skill files (copy bytes; never `os.symlink`), count skills for the summary, and render `${skills_list}` as one `- \`<name>\` — <description>` line per bundled skill, falling back to `None installed yet.` when there are none (the list is a snapshot as of creation; refresh never updates the README, FR-023)
- [X] T051 [US3] Run `python3 -m pytest tests/integration/test_init.py` and fix failures until green; then follow quickstart.md §7 by hand with a temporary skill folder under `src/cairn/assets/skills/` (remove it afterwards), opening the engagement in Claude Code to confirm the skill is listed with no setup (SC-005). Note: the automated copy check passes; opening an engagement in Claude Code is left as a manual check because no skill ships yet (R20)

**Checkpoint**: US1–US3 work. Bundled skills are available in a new engagement without setup.

---

## Phase 6: User Story 4 - Refresh framework files in an existing engagement (Priority: P3)

**Goal**: `cairn refresh [PATH]` brings templates and manifest-listed skills up to the running
framework version, protects edited files (confirm + backup), never touches content, and is
all-or-nothing.

**Independent Test**: quickstart.md §8. Create an engagement at fixture version 0.1.0, add content
to every content folder, edit `_templates/observation.md`, bump the fixture to 0.2.0 with a changed
`finding.md` and a new skill, run `cairn refresh`: `finding.md` updated, skill added,
`observation.md` kept and reported, `framework_version: "0.2.0"`, `tree_hash` of all content
unchanged.

### Tests for User Story 4

- [X] T052 [P] [US4] Create `tests/integration/test_refresh.py` covering quickstart §8 steps 1–6 and the decision table in contracts/framework-manifest.md: setup helper creates an engagement with `fixture_assets(version="0.1.0")` and `--no-git`, then writes a sample file into every content folder (`_inbox/`, `10-sources/raw/`, `10-sources/extracted/`, `20-research/`, `30-observations/`, each `40-synthesis/*`, `50-options/`, `70-views/`, `80-deliverables/`) and appends to a charter file and a log file; `test_update_add_keep_edited` (non-TTY: `finding.md` updated, new skill added under `.claude/skills/`, edited `observation.md` kept and listed under `kept (edited, not replaced)`, `engagement.md` differs from before only on the `framework_version:` line, manifest version `0.2.0`, `tree_hash` of everything except `_templates/`, `.claude/skills/`, `.cairn/` and `engagement.md` unchanged — SC-004, FR-023); `test_replace_edited` (`--replace-edited` replaces `observation.md` and the consultant's bytes are in `.cairn/backups/<YYYYMMDD-HHMMSS>/_templates/observation.md`); `test_tty_confirm` (in-process `refresh_cmd.run(..., confirm=...)` with a confirm callback answering `True` for one file and `False` for another); `test_remove` (template dropped from the fixture and unchanged in the engagement is deleted; dropped but edited is kept and removed from the manifest); `test_deleted_framework_file_readded`; `test_existing_unlisted_path_treated_as_edited`; `test_consultant_skill_untouched` (a `.claude/skills/my-own/SKILL.md` not in the manifest is byte-identical after refresh); `test_newer_engagement_refused` (engagement at 0.2.0, running 0.1.0 → exit 1, both versions in stderr, `tree_hash` unchanged); `test_not_an_engagement` (`cairn refresh <tmp_path>` → exit 1, `not a Cairn engagement`); `test_missing_manifest` (exit 1); `test_nothing_to_change` (second refresh exits 0); `test_rollback` (in-process: monkeypatch `os.replace` to fail on the second call → `CairnError`, every framework file, the manifest and `engagement.md` byte-identical to before, and any backup written before the failure still exists)

### Implementation for User Story 4

- [X] T053 [US4] Create `src/cairn/refresh_cmd.py` checks and planning (R17, contracts/cli.md → refresh checks 1–4): `run(path, *, replace_edited=False, confirm=None) -> Report`; (1) `engagement.md` exists and `read_front_matter(...)["type"] == "engagement"`, else `CairnError("not a Cairn engagement: <path>")`; (2) `layout.read_manifest(path)` succeeds; (3) `parse_version(engagement framework_version) <= parse_version(framework_version())`, else `CairnError` naming both versions; (4) `safety.check_assets(assets_root())`. Then build a plan: for every path in `manifest["files"] ∪ framework_files()`, classify with E/M/F exactly as the framework-manifest.md decision table into `add`, `keep`, `keep-rehash`, `update`, `edited`, `remove`, `keep-dropped` or `drop`, where a path in F but not in the manifest that already exists counts as `edited`. Only paths under `_templates/` and the `.claude/skills/<name>/` folders that appear in the manifest or in the running framework are ever considered
- [X] T054 [US4] Implement apply in `src/cairn/refresh_cmd.py` (depends on T053): for each `edited` path, call `confirm(path)` when given (TTY), else use `replace_edited`; replaced edited files are first copied to `.cairn/backups/<datetime.now():%Y%m%d-%H%M%S>/<path>`. Before writing, read original bytes of every path to change into memory. Write each new file to a temp file in the same folder and `os.replace` it into place; create missing parent folders for `add`; delete `remove` files and then their skill folder if it became empty. The restore scope covers every write in this task, including the final manifest and `engagement.md` writes below: read the original bytes of `.cairn/manifest.json` and `engagement.md` into memory up front, and write both with the same temp-file + `os.replace` method. On any exception, at any step, restore every changed file (framework files, manifest, `engagement.md`) from memory and delete every added file, but keep any backups made this run (backups are never deleted by the tool, contracts/framework-manifest.md → Guarantees), and raise `CairnError("refresh failed: <reason>; restored original files")`. Only after all file writes succeed: write the new manifest (`build_manifest` over the resulting framework file set, excluding `keep-dropped`/`drop` paths and keeping kept-edited files with their *old* manifest hash so they stay detected as edited) and replace the single `framework_version:` line inside the `engagement.md` front matter with `framework_version: "<new>"` (regex on that one line, preserving any trailing comment; no other change). Fill `Report` (`updated`, `added`, `removed`, `kept_edited`, `backed_up`, `previous_version`, `framework_version`)
- [X] T055 [US4] Add the `refresh` subcommand to `src/cairn/cli.py`: positional `PATH` (default `.`), `--replace-edited`; when `sys.stdin.isatty()`, pass a `confirm` callback that asks `<path> was edited in this engagement. Replace it (your version is backed up)? [y/N]` and returns `True` only for `y`/`yes`; print the summary in the shape of contracts/cli.md (`Refreshed <id>: framework <old> → <new>`, one line each for `updated:`, `added:`, `removed:`, `kept (edited, not replaced):`, `backed up:` when non-empty, then `Content folders untouched. Suggested: git add -A && git commit -m "Refresh Cairn to <new>"`). Refresh never runs git
- [X] T056 [US4] Run `python3 -m pytest tests/integration/test_refresh.py` and fix failures until green

**Checkpoint**: All four user stories work independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, audits and end-to-end validation

- [X] T057 [P] Add a "Creating an engagement" section to the repo-root `README.md`: install (`python3 -m pip install -e .` or `uv tool install --editable .`), `cairn init` / `cairn refresh` usage with a synthetic example, where framework assets live (`src/cairn/assets/{seed,templates,skills}/`, R4), and that engagements must be created outside this repo (FR-012)
- [X] T058 [P] Add `test_no_network_or_remote` to `tests/unit/test_safety.py`: scan every `src/cairn/**/*.py` source and assert it imports none of `socket`, `urllib`, `http`, `ftplib`, `smtplib`, `ssl` and never contains the strings `remote add`, `push` or `fetch` in a git argument list (FR-018); also assert no `os.symlink` call exists (R10)
- [X] T059 [P] Add `test_init_is_fast` and `test_refresh_is_fast` to `tests/integration/test_init.py` and `tests/integration/test_refresh.py`: each subprocess run with `--no-git` completes in under 2 s wall-clock (plan → Performance Goals)
- [X] T060 Review all 12 templates and 12 seeds against the constitution's Skill Contract and data-model §3–§4: `status: proposed`, `audience: internal`, `inference_confirmed: false`, provenance fields present, ID placeholders only, no client names; fix any drift in `src/cairn/assets/`
- [X] T061 Run the full suite `python3 -m pytest` and every manual scenario in `specs/001-engagement-init/quickstart.md` (§1–§9, using synthetic names only) in a `mktemp -d` scratch folder outside the repo; record any deviation and fix it before marking the feature done

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T001 first; T002–T004 then in parallel.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories.
  - T005, T006, T007, T010, T011, T012 in parallel; T008 after T006; T009 after T005;
    T013 after T008; T014 last.
- **US1 (Phase 3)**: Depends on Foundational.
- **US2 (Phase 4)**: Depends on US1 (it adds checks, merge mode and options to `init_cmd.py`
  and `cli.py`, which US1 creates).
- **US3 (Phase 5)**: Depends on US1 only. It can run in parallel with US2 if the two
  developers coordinate edits to `init_cmd.py` (T045 vs T050).
- **US4 (Phase 6)**: Depends on US1 (engagements with a manifest), US2 (`safety.check_assets`
  from T044) and US3 (T049 puts skills in `framework_files()`; without it, refresh can't add,
  update or protect skills, FR-024, and T052's skill tests fail).
- **Polish (Phase 7)**: After all desired stories.

### Within Each User Story

- Tests are written first and must fail before implementation.
- Assets (templates, seeds) before `init_cmd.py`; `gitutil.py` before `init_cmd.py`;
  `init_cmd.py` before `cli.py` wiring.
- Each story ends with a "run tests and fix" task that must be green before moving on.

### Same-File Sequences (never parallel)

- `src/cairn/cli.py`: T009 → T039 → T046 → T055
- `src/cairn/init_cmd.py`: T038 → T045 → T050
- `src/cairn/layout.py`: T008 → T049
- `src/cairn/refresh_cmd.py`: T053 → T054
- `tests/unit/test_layout.py`: T013 → T015
- `tests/integration/test_init.py`: T016 → T048 → T059
- `tests/unit/test_safety.py`: T041 → T058

---

## Parallel Examples

### Phase 2: Foundational

~~~bash
Task: "T005 Create src/cairn/report.py"
Task: "T006 Create src/cairn/textutil.py"
Task: "T007 Create src/cairn/transaction.py"
Task: "T010 Create tests/conftest.py"
Task: "T011 Create tests/unit/test_textutil.py"
Task: "T012 Create tests/unit/test_transaction.py"
~~~

### User Story 1

~~~bash
# Tests together:
Task: "T015 Template validation in tests/unit/test_layout.py"
Task: "T016 tests/integration/test_init.py"
Task: "T017 tests/integration/test_git.py"

# All 12 templates and 7 seed tasks together (19 independent files/groups):
Task: "T018 src/cairn/assets/templates/source.md"
Task: "T019 src/cairn/assets/templates/observation.md"
...
Task: "T029 src/cairn/assets/templates/lesson.md"
Task: "T030 src/cairn/assets/seed/README.md"
...
Task: "T036 src/cairn/assets/seed/60-log/*.md"
~~~

### User Story 2

~~~bash
Task: "T041 tests/unit/test_safety.py"
Task: "T042 tests/integration/test_init_safety.py"
Task: "T043 tests/integration/test_init_merge.py"
~~~

### User Story 4

~~~bash
# Test file first, then the two refresh_cmd.py tasks in sequence, then cli wiring.
Task: "T052 tests/integration/test_refresh.py"
~~~

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup
2. Phase 2: Foundational
3. Phase 3: US1 (SC-001 and SC-007 depend on people, so they are checked by hand in T061;
   T059 only times the tool itself)
4. **Stop and validate**: quickstart §1–§3 and `check_layout()` pass
5. Usable for hand-written work on a synthetic engagement

US1 alone is not safe for real client work: the framework-repo, nested-engagement and code-name
protections arrive in US2. Treat **US1 + US2 (both P1)** as the minimum before any real
engagement is created.

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → engagement creation works (internal demo only)
3. US2 → safe for real engagements (first release)
4. US3 → skills copied; ready for the `charter` feature
5. US4 → engagements can follow framework updates mid-engagement

### Parallel Team Strategy

1. Everyone finishes Setup + Foundational together.
2. Developer A: US1 code (T037–T039); Developer B: templates T018–T029; Developer C: seeds
   T030–T036 and tests T015–T017.
3. After US1: A takes US2, B takes US3 (coordinate on `init_cmd.py`), C writes US4 tests (T052).

---

## Notes

- [P] tasks touch different files and have no dependency on an incomplete task.
- Only synthetic names (Acme, Globex, Falcon) appear in tests and fixtures (Principle VIII).
- No test may create files inside the Cairn repo; integration tests work only in `tmp_path`.
- Commit after each task or logical group, focusing the message on why.
