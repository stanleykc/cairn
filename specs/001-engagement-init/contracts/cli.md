# Contract: `cairn` command line

Invocation: `cairn <subcommand> [options]`, or `python3 -m cairn <subcommand> [options]`.

Global: `cairn --version` prints `cairn <version>`. `cairn --help` and
`cairn <subcommand> --help` show usage.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (including refresh with nothing to change) |
| 1 | Refused or failed. Nothing was left behind (init) or originals were restored (refresh). |
| 2 | Usage error: a bad or missing argument when not on a TTY. Nothing was written. |
| 130 | Interrupted (Ctrl-C). Rollback completed. |

Errors and refusals go to stderr in the form `cairn: error: <reason>`, followed by a
`hint:` line when there is a fix to suggest. Summaries go to stdout.

---

## `cairn init [PATH]`

Creates a new engagement.

| Argument / option | Required | Default | Notes |
|---|---|---|---|
| `PATH` | no | `./<client-or-code>-<engagement>` | Engagement folder. `.` means the current folder. If given, its basename is the `id` (after slugify, R15). |
| `--engagement NAME` | yes* | — | Engagement name, as typed |
| `--client NAME` | yes* unless `--code-name` is given | — | Real client name. When a code name is used, it's optional and is stored only in `engagement.md`. |
| `--code-name CODE` | no | — | Used instead of the client name for the folder, `id`, README, summary and commit message (FR-016) |
| `--lead NAME` | yes* | `git config user.name`, then `$USER` | Lead consultant |
| `--team NAME` | no | — | Repeatable |
| `--start-date YYYY-MM-DD` | no | today | |
| `--model-use {allowed,restricted,unconfirmed}` | no | `unconfirmed` | FR-015 |
| `--merge` | no | off | Allow a non-empty existing folder. Adds only missing items (FR-013). |
| `--no-git` | no | off | Skip version control (FR-021) |

\* Required means: if the value is missing and stdin is a TTY, the command prompts for it.
If stdin isn't a TTY, it exits with code 2. Prompts, in order:
1. Engagement name
2. Client code name (optional, blank = none)
3. Client name (required if there is no code name; otherwise optional, blank = leave it out)
4. Lead consultant (default shown)
5. Model-use policy (default `unconfirmed`)

All prompts come before anything is written.

### Checks, in order. Any failure stops the command before it writes anything.

1. The inputs are valid (non-empty slug, ISO date, policy value).
2. The target isn't inside the Cairn framework repository (R11).
3. Neither the target nor any ancestor is an engagement (R12). In merge mode, if the
   target itself is an engagement, the hint says to use `cairn refresh`.
4. The target either doesn't exist, is empty, or `--merge` was given. When it refuses, it
   lists up to 10 conflicting entries and suggests a distinct name, such as `<id>-2`.
5. The parent (or the target, if it exists) is writable.
6. The framework assets are complete: every seed file and all 12 templates are present.
   It lists any missing.
7. Git preflight, unless `--no-git` (R14).

### Effects

- Creates the canonical folders (data-model §5), the seed files (§4), `_templates/*` (§3),
  `.claude/skills/<name>/**` for every bundled skill, `.cairn/manifest.json`, and a
  `.gitkeep` in each empty canonical folder created.
- In merge mode, skips every path that already exists and never writes inside an existing
  `10-sources/raw/`.
- Git: `git init` plus an initial commit, or skipped as described in R14. Never adds a
  remote.
- Makes no network access of any kind.

### Summary (stdout)

~~~text
Created engagement acme-fulfillment-review at /path/acme-fulfillment-review
  framework 0.1.0 · 16 folders · 12 seed files · 12 templates · 0 skills
  git: initialized, initial commit a1b2c3d (no remote)

! Model-use policy is UNCONFIRMED. Set model_use in engagement.md before ingesting
  any source.

Next steps:
  1. Confirm the client's model-use policy (engagement.md, 00-charter/scope.md)
  2. Run the `charter` skill from inside the engagement folder
  3. Put original files in 10-sources/raw/
~~~

In merge mode, a `Skipped (already present):` list comes before the next steps.

---

## `cairn refresh [PATH]`

Updates the framework-provided files in an existing engagement.

| Argument / option | Required | Default | Notes |
|---|---|---|---|
| `PATH` | no | `.` | Engagement root |
| `--replace-edited` | no | off | Without a TTY, replace edited framework files (after backing them up) instead of keeping them |

### Checks, in order. Any failure stops the command with no change.

1. `PATH/engagement.md` exists and has `type: engagement`. If not, it says "not a Cairn
   engagement".
2. `PATH/.cairn/manifest.json` exists and parses.
3. `engagement.framework_version` ≤ the running version. If not, it reports both versions.
4. The framework assets are complete.

### Effects

These follow the decision table in [framework-manifest.md](framework-manifest.md).
Refresh writes only to `_templates/`, the manifest-listed `.claude/skills/<name>/`
folders, `.cairn/`, and the `framework_version:` line of `engagement.md`.

On a TTY it asks about each edited file:
`_templates/finding.md was edited in this engagement. Replace it (your version is backed up)? [y/N]`

### Summary (stdout)

~~~text
Refreshed acme-fulfillment-review: framework 0.1.0 → 0.2.0
  updated: _templates/finding.md, .claude/skills/ingest/SKILL.md
  added:   .claude/skills/synthesize/SKILL.md
  kept (edited, not replaced): _templates/observation.md
  backed up: .cairn/backups/20261124-101500/_templates/option.md
Content folders untouched. Suggested: git add -A && git commit -m "Refresh Cairn to 0.2.0"
~~~
