# Contract: Framework manifest (`.cairn/manifest.json`)

This is tool bookkeeping written by `cairn init` and rewritten by `cairn refresh`. It is
not engagement content. If it is deleted, refresh refuses and treats the folder as damaged.
Rebuilding the manifest is out of scope for this feature.

## Schema

~~~json
{
  "schema": 1,
  "framework_version": "0.1.0",
  "written": "2026-11-03T14:05:00",
  "files": {
    "_templates/observation.md": "sha256:9f2c…",
    ".claude/skills/charter/SKILL.md": "sha256:41ab…"
  }
}
~~~

- Paths are POSIX, relative to the engagement root, and sorted.
- `files` lists every framework-provided file: everything under `_templates/`, plus every
  file of each bundled skill, plus `.claude/settings.json` when any bundled skill declares
  `Bash(...)` rules in its `allowed-tools` (framework 0.2.0; the file pre-approves exactly
  those rules for the engagement). Seed files are **not** listed. They belong to the
  engagement once they are created.
- A skill folder in `.claude/skills/` that isn't in `files` belongs to the consultant, and
  refresh never touches it.

## Refresh decision table

Definitions: **E** is the engagement's current bytes, **M** is the hash recorded in the
manifest, **F** is the running framework's bytes.

| E exists | hash(E) = M | F exists | hash(E) = hash(F) | Action |
|---|---|---|---|---|
| no | — | yes | — | **add** (also when the consultant deleted a framework file) |
| yes | yes | yes | yes | **keep** |
| yes | yes | yes | no | **update** |
| yes | no | yes | yes | **keep** (record the new hash) |
| yes | no | yes | no | **edited**: confirm → back up to `.cairn/backups/<ts>/<path>`, then replace. Otherwise keep and report. |
| yes | yes | no | — | **remove** |
| yes | no | no | — | **keep** (edited, no longer provided). Drop it from the manifest and report it. |
| no | — | no | — | drop it from the manifest |

A path in F that isn't in the manifest but already exists in the engagement (for example,
the consultant created a file with the same name) is treated as **edited**.

## Guarantees

- No path outside `_templates/`, the manifest-listed skill folders and `.cairn/` is created,
  changed or deleted. The one exception is the `framework_version:` line of
  `engagement.md`.
- Refresh is all-or-nothing. If any write fails, every file it changed is restored from
  memory, and the manifest and `engagement.md` are left unchanged.
- Backups are never deleted by the tool.
