# Quickstart: Validating Engagement Initialization

Run these checks after implementation to show the feature works end to end. They use
only synthetic names ("Acme", "Globex"), per Principle VIII. Command details are in
[contracts/cli.md](contracts/cli.md). File schemas are in [data-model.md](data-model.md).

## Prerequisites

- Python 3.11+ (`python3 --version`), `git` with `user.name` and `user.email` set
- A checkout of the Cairn repo

## Setup

~~~bash
cd /path/to/cairn
python3 -m pip install -e '.[dev]'      # or: uv tool install --editable .  (CLI only)
cairn --version                          # → cairn 0.1.0
export WORK="$(mktemp -d)"               # scratch area OUTSIDE the framework repo
~~~

## Automated suite

~~~bash
python3 -m pytest                        # all unit + integration tests
python3 -m pytest tests/integration -k layout     # SC-002 layout check only
~~~

Expected: every test passes. The suite covers each scenario below, plus fault
injection for rollback (FR-017).

## Manual scenarios

### 1. Create an engagement (US1, SC-001, SC-002)

~~~bash
cd "$WORK"
time cairn init --engagement "Fulfillment Review" --client "Acme" --lead "Test Lead"
find acme-fulfillment-review -type d -not -path '*/.*' | sort
~~~

Expected:
- The folder `acme-fulfillment-review/` contains exactly the 16 canonical folders
  (data-model §5).
- `README.md`, `engagement.md`, six `00-charter/*.md` files, `10-sources/index.md` and
  three `60-log/*.md` files are present.
- `_templates/` holds 12 files, each with `status: proposed` and `audience: internal`.
- `grep -rE '\b[A-Z]-[0-9]{3}\b' acme-fulfillment-review --include='*.md'` finds no real
  IDs (FR-007).
- The summary lists next steps and flags the model-use policy as UNCONFIRMED.

### 2. Interactive prompts (US1-4)

~~~bash
cd "$WORK" && cairn init
~~~

Expected: it asks for engagement name, client, code name, lead and model-use policy, in
that order, before writing anything. Press Ctrl-C at any prompt: exit code 130, and no
folder is created.

### 3. Version control (US1-5, FR-018, FR-021)

~~~bash
cd "$WORK/acme-fulfillment-review"
git log --oneline          # one commit: "Initialize engagement acme-fulfillment-review (cairn 0.1.0)"
git remote                 # empty
git status --porcelain     # empty
~~~

Then `cairn init --no-git ...` in a new location. Expected: no `.git/`.

### 4. Safety refusals (US2, SC-003)

| Command | Expected |
|---|---|
| `cd /path/to/cairn && cairn init --engagement X --client Acme --lead T` | Exit 1, "inside the Cairn framework repository", no files written |
| `cd "$WORK/acme-fulfillment-review/20-research" && cairn init --engagement X --client Globex --lead T` | Exit 1, "inside another engagement" |
| `cd "$WORK" && cairn init --engagement "Fulfillment Review" --client Acme --lead T` (second time) | Exit 1, lists conflicts, suggests `acme-fulfillment-review-2` |
| `mkdir "$WORK/ro" && chmod a-w "$WORK/ro" && cairn init "$WORK/ro/e" --engagement X --client Acme --lead T` | Exit 1, "not writable" |
| `cairn init --engagement X --client Acme --lead T < /dev/null` with `--engagement` removed | Exit 2, names the missing `--engagement` |

### 5. Model-use policy and code name (US2-4 to US2-6, SC-006)

~~~bash
cd "$WORK"
cairn init --engagement "Pricing Study" --client "Globex Corporation" --code-name "Falcon" \
  --lead T --model-use restricted
grep -E '^(id|client|client_code_name|model_use):' falcon-pricing-study/engagement.md
ls "$WORK" | grep -i globex    # no output
~~~

Expected: `id: "falcon-pricing-study"` and `model_use: restricted`.
`grep -rl Globex falcon-pricing-study --exclude-dir=.git` lists only `engagement.md`, and
`git -C falcon-pricing-study log --format=%B` doesn't contain "Globex". Repeat with
`--client` omitted (code name only): grep finds nothing. With `--model-use` omitted, `engagement.md` and
`00-charter/scope.md` both show `unconfirmed`.

### 6. Merge into an existing folder (US2-3, FR-013, SC-004)

~~~bash
mkdir -p "$WORK/existing/10-sources/raw" && echo "orig" > "$WORK/existing/10-sources/raw/brief.pdf"
echo "# mine" > "$WORK/existing/README.md"
cairn init "$WORK/existing" --merge --engagement X --client Acme --lead T
cat "$WORK/existing/README.md"            # still "# mine"
cat "$WORK/existing/10-sources/raw/brief.pdf"   # still "orig"; no .gitkeep added in raw/
~~~

Expected: the summary lists `README.md` under "Skipped", and all missing items are created.

### 7. Skills available (US3, SC-005)

With at least one skill in `src/cairn/assets/skills/`, create an engagement, open the
folder in Claude Code and run `/charter` (once the `charter` feature has landed). Until
then, `tests/integration/test_init.py::test_skills_copied` checks the copy mechanism with
a fixture skill (research R20). Expected: `.claude/skills/<name>/SKILL.md` exists as a
regular file (not a symlink), and the README lists the skill.

### 8. Refresh (US4, SC-004)

The integration test `tests/integration/test_refresh.py` runs this scenario:
1. Create an engagement with a fixture framework at version 0.1.0, and add sample files to
   every content folder.
2. Edit `_templates/observation.md`. Bump the fixture framework to 0.2.0 with a changed
   `finding.md` and a new skill.
3. Run `cairn refresh`. Expected: `finding.md` updated, the skill added,
   `observation.md` kept (non-TTY) and reported, and `framework_version: "0.2.0"`. The
   tree hash of every content folder, `README.md` and the charter is unchanged.
4. Run with `--replace-edited`. Expected: the backup is in `.cairn/backups/<ts>/`.
5. Run a 0.1.0 framework against the 0.2.0 engagement. Expected: exit 1 with a version
   mismatch.
6. Run `cairn refresh "$WORK"` (not an engagement). Expected: exit 1, "not a Cairn
   engagement".

### 9. README usability (SC-007)

Give a colleague who is new to Cairn only the generated `README.md`. Within 10 minutes they
should correctly say that originals go in `10-sources/raw/` and that agent output waiting
for review is in `_inbox/`.

## Cleanup

~~~bash
rm -rf "$WORK"
~~~
