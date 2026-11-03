# Research: Engagement Initialization

Phase 0 decisions for [plan.md](plan.md). The Technical Context had no open
NEEDS CLARIFICATION items. Each decision below settles a design choice the spec leaves open.

## R1. Language and runtime

- **Decision**: Python 3.11+, using only the standard library at runtime.
- **Rationale**: Consultants run macOS and Linux, and both have `python3`. The tasks
  (folders, file copies, hashing, prompts, calling `git`) don't need any third-party
  library. With no dependencies there's no supply-chain risk and nothing to install beyond
  the tool itself. 3.11 is the minimum because of `tomllib` (see R11).
- **Alternatives considered**: Bash, like the Spec Kit scripts. Rollback, Unicode slugs and
  hashing are fragile in Bash, and it's harder to test. Typer/Click, like `specify`: they
  give nicer help output but add dependencies, and `argparse` is enough for two subcommands.

## R2. Distribution and invocation

- **Decision**: `pyproject.toml` (hatchling) defines the package `cairn` with the console
  script `cairn = "cairn.cli:main"`. It can be installed from a checkout with
  `uv tool install --editable .` or `python3 -m pip install -e .`. As a fallback,
  `python3 -m cairn` works from an activated environment.
- **Rationale**: One command on the PATH, like `specify init`. An editable install means
  consultants get framework updates with `git pull`, and their engagements stay unchanged
  until they run `cairn refresh`.
- **Alternatives considered**: A bare script in `bin/`. It has to find its assets relative
  to itself and can't be installed cleanly. Publishing to PyPI isn't needed for a team
  of this size yet.

## R3. CLI shape

- **Decision**: `argparse` with subcommands `init` and `refresh`. The flags and behavior
  are in [contracts/cli.md](contracts/cli.md). The tool prompts for a missing required
  input only when stdin is a TTY. Otherwise it exits with a usage error (exit code 2) that
  names the missing flags (FR-003).
- **Rationale**: Works the same in unattended and interactive use. Checking for a TTY
  stops a script from hanging on a prompt.
- **Alternatives considered**: Always prompting. That breaks automation and tests.

## R4. Where framework assets live

- **Decision**: As package data under `src/cairn/assets/{seed,templates,skills}/`, read
  with `importlib.resources.files("cairn") / "assets"`.
- **Rationale**: The assets are found the same way in editable and normal installs. The
  hatchling src layout includes package data with no extra build configuration.
- **Alternatives considered**: Top-level `skills/` and `templates/` folders, included
  with `force-include`. They are easier to find, but they need build configuration and
  behave differently in editable and wheel installs. A pointer in the repo README makes up
  for the lower visibility.

## R5. Rendering seed files

- **Decision**: Seed files are `string.Template` files (`${name}` placeholders), rendered
  with `substitute()` so that a missing value raises an error. Every value placed in YAML
  front matter goes through `json.dumps()`, because a JSON string is a valid YAML
  double-quoted scalar. That handles quotes, colons, `#` and accents safely. Object
  templates are copied byte for byte, with no rendering.
- **Rationale**: No YAML library at runtime, and names supplied by consultants can't break
  the front matter.
- **Alternatives considered**: Jinja2, a dependency the tool doesn't need. Hand-escaping
  YAML is error-prone.

## R6. Reading front matter

- **Decision**: A minimal reader in `textutil.py` that returns the top-level `key: value`
  scalars between the first two `---` lines. Only `type` and `framework_version` are ever
  read by the tool. Tests check all generated front matter with PyYAML as an independent
  validator.
- **Rationale**: The tool reads only flat scalars it wrote itself. A full parser would be
  the only reason to add a runtime dependency.
- **Alternatives considered**: PyYAML at runtime. It's the only dependency the tool would
  have, and it isn't needed.

## R7. The engagement record

- **Decision**: `engagement.md` at the engagement root, with YAML front matter
  (`type: engagement`) and a short body explaining each field. The schema is in
  [contracts/engagement-record.md](contracts/engagement-record.md).
- **Rationale**: Placing it at the root makes it easy to find and makes a folder easy to
  detect as an engagement (R12). Later skills, such as `ingest` checking `model_use`, have
  one fixed place to read. `00-charter/scope.md` shows the policy too (FR-015), but
  `engagement.md` is the authoritative copy.
- **Alternatives considered**: Putting the settings in README front matter. The README is
  narrative and consultants are encouraged to edit it, so settings would mix with prose.

## R8. Framework manifest and edit detection

- **Decision**: `.cairn/manifest.json` records the framework version and the SHA-256 of
  every framework-provided file as it was written. Refresh compares each file's current
  hash with the recorded one: if they differ, the consultant edited the file. The schema is
  in [contracts/framework-manifest.md](contracts/framework-manifest.md).
- **Rationale**: Edits must be detected even with `--no-git`, and the master template for
  an older version isn't available at refresh time. The manifest is tool bookkeeping and
  can be rebuilt. Engagement content never lives in it, so it doesn't conflict with
  FR-009 or Principle I. Spec Kit tracks its installed files the same way
  (`.specify/integrations/*.manifest.json`).
- **Alternatives considered**: Hashes in the `engagement.md` front matter. That clutters a
  file people read, and refresh would have to rewrite a file the consultant edits. Git
  history doesn't work when version control is opted out. A YAML/markdown manifest would
  need a nested YAML writer and reader with no YAML library.

## R9. Hidden tool folders and the canonical layout

- **Decision**: The layout check (SC-002) compares only folders whose names don't start
  with `.`. `.git/`, `.claude/` and `.cairn/` are tool folders outside the canonical
  content layout.
- **Rationale**: FR-019 requires `.claude/skills/`, and FR-021 requires `.git/`, so FR-004
  ("no other folders") has to mean content folders. Skills that scan content folders
  already skip dot-folders.
- **Alternatives considered**: Putting the manifest in `_templates/`. That mixes tool
  bookkeeping with templates the skills read, and the manifest also covers skills.

## R10. Where skills are copied

- **Decision**: Each skill in `assets/skills/<name>/` is copied, folder and all, to
  `<engagement>/.claude/skills/<name>/` (the project skills folder Claude Code reads). The
  tool copies and never symlinks. Refresh touches only skills listed in the manifest, so
  skills the consultant added themselves are never touched.
- **Rationale**: SC-005 needs skills to work with no setup. Copying keeps the engagement
  self-contained and pinned to its version (FR-019, US4-1).
- **Alternatives considered**: Symlinks to the framework checkout. Skills would change
  without a refresh, and moving or archiving the folder would break them
  (`allow_symlinks: false` is also the Spec Kit setting here). A user-level skills folder
  would be shared across engagements and not pinned to a version.

## R11. Detecting the framework repository

- **Decision**: Refuse when the target, or any of its ancestors, contains a `pyproject.toml`
  whose `[project].name` is `"cairn"` (read with `tomllib`). Also refuse when the target is
  inside the folder that holds the running package's own project root (editable install).
- **Rationale**: The common mistake is running `cairn init` inside the Cairn checkout. Both
  checks are deterministic and need no marker file (SC-003).
- **Alternatives considered**: A dedicated `.cairn-framework` marker file, one more file to
  keep. Matching the constitution header only works if `.specify/` is present.

## R12. Detecting nested engagements

- **Decision**: Refuse when any ancestor of the target has an `engagement.md` whose front
  matter has `type: engagement`, or has a `.cairn/manifest.json`. In merge mode, also refuse
  when the target itself is already an engagement, and point to `cairn refresh`.
- **Rationale**: Nested engagements would mix up ID assignment and confidentiality
  boundaries (spec, edge cases).

## R13. All-or-nothing creation and rollback

- **Decision**: All checks run before anything is written. A `Transaction` then records
  every path it creates, in order. If anything goes wrong (an exception, `KeyboardInterrupt`,
  or a failed git step), it deletes the files it created in reverse order, then removes
  each folder it created if the folder is empty, then deletes `.git/` if this run created
  it. It never deletes a path that existed before the run. Each file is written with
  exclusive create (`open(..., "x")`), so a file that appears during the run is never
  overwritten.
- **Rationale**: Meets FR-017 and the "interrupted partway" edge case without having to
  stage everything in a temporary folder and move it into place (which doesn't work in
  merge mode).
- **Alternatives considered**: Building in a temp folder and renaming it into place. That
  is atomic for new folders but not for merge mode, and it fails across filesystems.

## R14. Version control

- **Decision**:
  - Preflight (before anything is written, unless `--no-git`): `git` is on the PATH, and
    `git config user.name` and `user.email` are set. If either check fails, stop and
    suggest the fix or `--no-git`.
  - If the target is already inside a git work tree (`git rev-parse --is-inside-work-tree`),
    don't run `git init` and don't commit, because the tool shouldn't commit into someone
    else's repository. Tell the consultant, and warn if that repository has a remote
    (`git remote` returns something).
  - Otherwise: `git init`, `git add -A`, then
    `git commit -m "Initialize engagement <id> (cairn <version>)"`. No remote is ever added.
  - A `.gitkeep` goes in every empty canonical folder the run creates, so clones keep the
    layout. No `.gitignore` is written, so everything, raw originals included, is tracked
    (FR-021).
- **Rationale**: FR-018 and FR-021, and the confidentiality risk of an existing repo with
  a remote.
- **Alternatives considered**: A git library (dulwich or pygit2), an unnecessary dependency.

## R15. Folder-name rules

- **Decision**: `slugify(s)`: NFKD-normalize, drop combining marks, lowercase, turn every
  run of non-`[a-z0-9]` characters into one `-`, and trim `-` from both ends. The folder
  name is `slugify(code_name or client) + "-" + slugify(engagement)`. An empty result is a
  usage error. An explicit folder argument is used as given.
- **Example**: `"Société Générale"` + `"Q4: Fulfillment Review!"` →
  `societe-generale-q4-fulfillment-review`.

## R16. Format of entries in collection files

- **Decision**: Questions, hypotheses, assumptions, decisions and lessons are entries inside
  one file each (`00-charter/*.md`, `60-log/*.md`), as the framework design specifies. Each
  entry is a level-2 heading `## Q-001: <short title>`, followed by a fenced `yaml` block
  with the standard fields, then free text. The file itself has front matter
  `type: collection` and `holds: question`. The templates for these types contain one
  entry block. The templates for the other types (source, observation, research, finding,
  issue, opportunity, option) are whole files with front matter.
- **Rationale**: Keeps the design's file layout, keeps every object's fields
  machine-readable, and lets ID scanners find IDs with one heading pattern.
- **Alternatives considered**: One file per question or decision, which goes against the
  layout in the framework design. Bare markdown lists can't hold the standard fields.

## R17. How refresh behaves

- **Decision**:
  - Refuse when `engagement.md` is missing or isn't `type: engagement`, or when the
    engagement's `framework_version` is newer than the running version (FR-025).
  - For each framework file, decide what to do: *add* (new in the framework), *update* (the
    engagement copy is unchanged since it was written and the framework copy differs),
    *keep* (identical), *edited* (the engagement copy differs from its manifest hash), or
    *remove* (dropped from the framework and unchanged in the engagement).
  - *Edited* files: ask for confirmation one file at a time. If confirmed, first copy the
    consultant's version to `.cairn/backups/<YYYYMMDD-HHMMSS>/<path>`. Without a TTY, edited
    files are kept unless `--replace-edited` is given. A file that was edited and then
    dropped from the framework is kept.
  - All new contents are computed first, and original bytes are kept in memory. Writes use
    a temp file plus `os.replace`. If anything fails, originals are restored. Only on
    success is the manifest rewritten and the single `framework_version:` line in
    `engagement.md` replaced (no other edit to that file).
  - Prints the list of added, updated, removed, kept-edited and backed-up files. Doesn't
    commit, and suggests a commit.
- **Rationale**: FR-022 to FR-025 and US4. Edited skills are handled the same way as edited
  templates, which costs nothing.

## R18. Framework version

- **Decision**: Semantic version in `src/cairn/__init__.py` (`__version__ = "0.1.0"`), read
  by hatchling (`[tool.hatch.version]`). Versions are compared as integer tuples. A
  pre-release suffix is ignored when comparing.
- **Rationale**: One source of truth for the version, used by the engagement record, the
  manifest and the refresh check.

## R19. Testing strategy

- **Decision**: `pytest`. Unit tests cover `slugify`, the front-matter reader, the safety
  checks and transaction rollback. Integration tests run `python3 -m cairn` as a subprocess
  in `tmp_path`, with `GIT_CONFIG_GLOBAL` pointing at a temporary gitconfig that holds a
  synthetic identity. Helpers:
  - `check_layout(path)`, which lives in `layout.py` so a later health-check command can
    reuse it: exact match of the non-dot folders, every seed file present, every `.md`
    front matter parses with PyYAML, and no numbered object exists.
  - `tree_hash(path, exclude)`: a map from path to SHA-256, compared before and after to
    prove nothing changed (SC-004).
  - Fault injection: monkeypatch a write to fail after N files, then assert the folder is
    back to its state before the run (FR-017).
  - Fixture framework: two test-only environment variables, read only in `layout.py`, let
    a subprocess run use a temporary copy of the assets at another version.
    `CAIRN_ASSETS_DIR` replaces the package assets folder, and `CAIRN_FRAMEWORK_VERSION`
    replaces `cairn.__version__`. This is how R20 adds a fixture skill and quickstart §8
    bumps the framework to 0.2.0.
  - The real-ID check uses only the 12 type prefixes (`\b[SOQHARFIPXDL]-\d{3}\b`). In a
    rendered engagement it skips `README.md` and `engagement.md`, which hold names the
    consultant typed. The unrendered seed files are checked instead.
  - Tests run in a virtual environment (`.venv`), because Homebrew's Python is externally
    managed (PEP 668).
- **Rationale**: Each success criterion can be checked automatically. Only synthetic names
  are used, such as "Acme" and "Globex" (Principle VIII).

## R20. Charter skill and SC-005

- **Decision**: This feature delivers the copy mechanism and an empty
  `assets/skills/` folder. Integration tests add a fixture skill to a temporary copy of the
  assets to prove copying, version pinning and refresh. That is how SC-005 ("every bundled
  skill can be invoked with no setup") is checked. `charter` is checked again when its own
  feature adds `assets/skills/charter/`. No placeholder skill is shipped (confirmed in
  clarification, 2026-11-03).
- **Rationale**: The spec assumes skills that aren't built yet are simply absent. A
  placeholder `charter` would show consultants a skill that doesn't work.
- **Alternatives considered**: Shipping a minimal `charter` skill now. That's scope creep
  into the next feature.
