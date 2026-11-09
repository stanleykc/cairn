"""The `extract-observations` skill ships with the framework (005) and the data model moved with it."""

import json
import re
from pathlib import Path

import yaml

from cairn import layout
from conftest import ACME_ID, INIT_ACME, PACKAGE_ASSETS, fixture_assets, run_cairn

SKILL_DIR = PACKAGE_ASSETS / "skills" / "extract-observations"
SKILLS = PACKAGE_ASSETS / "skills"
SKILL_FILES = (
    "SKILL.md",
    "reference/writing-observations.md",
    "reference/change-convention.md",
    "scripts/observe.py",
)
REPO = Path(__file__).resolve().parents[2]
CONTRACTS = REPO / "specs" / "005-extract-observations" / "contracts"
CONVENTION_002 = REPO / "specs" / "002-charter-skill" / "contracts" / "change-convention.md"
DESCRIPTION = (
    "Pull atomic, cited observations from ingested sources into _inbox/, tagged to the charter's "
    "questions. Use after ingest, or when a new question needs evidence from sources already ingested."
)
ARGUMENT_HINT = "[S-### …] [for Q-### …] [ignore <part>] [from <stakeholder>'s point of view]"
NEW_FIELDS = ("speaker", "passage_kind", "translated")


def init(tmp_path, git_env, env_extra=None) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    result = run_cairn(*INIT_ACME, "--no-git", cwd=work, env=git_env | (env_extra or {}))
    assert result.returncode == 0, result.stderr
    return work / ACME_ID


def test_init_ships_extract_observations(tmp_path, git_env):
    eng = init(tmp_path, git_env)
    manifest = json.loads((eng / ".cairn" / "manifest.json").read_text())
    for rel in SKILL_FILES:
        copied = eng / ".claude" / "skills" / "extract-observations" / rel
        assert copied.is_file() and not copied.is_symlink(), rel
        assert copied.read_bytes() == (SKILL_DIR / rel).read_bytes(), rel
        assert f".claude/skills/extract-observations/{rel}" in manifest["files"], rel
    settings = json.loads((eng / ".claude" / "settings.json").read_text())
    assert "Bash(python3 *observe.py*)" in settings["permissions"]["allow"]
    readme = (eng / "README.md").read_text()
    assert f"- `extract-observations` — {DESCRIPTION}" in readme
    template = (eng / "_templates" / "observation.md").read_text()
    for field in NEW_FIELDS:
        assert re.search(rf"^{field}:", template, re.M), field


def test_skill_front_matter():
    meta = yaml.safe_load((SKILL_DIR / "SKILL.md").read_text().split("---\n")[1])
    assert meta == {
        "name": "extract-observations",
        "description": DESCRIPTION,
        "argument-hint": ARGUMENT_HINT,
        "allowed-tools": "Read, Write, Edit, Bash(python3 *observe.py*)",
    }
    assert ("extract-observations", DESCRIPTION) in layout.bundled_skills(PACKAGE_ASSETS)


def test_no_placeholder_files_in_skill():
    names = [p.name for p in SKILL_DIR.rglob("*") if p.is_file()]
    assert ".gitkeep" not in names
    shipped = {rel.split("/extract-observations/", 1)[1] for rel in layout.framework_files(PACKAGE_ASSETS)
               if rel.startswith(".claude/skills/extract-observations/")}
    assert shipped == set(SKILL_FILES)


def test_template_has_observation_fields():
    text = (PACKAGE_ASSETS / "templates" / "observation.md").read_text()
    front = yaml.safe_load(text.split("---\n")[1])
    assert front["speaker"] == "" and front["passage_kind"] == "" and front["translated"] is False
    keys = list(front)
    assert keys[keys.index("derived") + 1 : keys.index("derived") + 4] == list(NEW_FIELDS)
    body = text.split("---\n", 2)[2]
    assert re.findall(r"^## (.+)$", body, re.M) == ["Claim", "Passage"]
    assert "\n> The exact words from the source at the locator.\n" in body


def test_change_convention_copies_identical():
    charter = (SKILLS / "charter" / "reference" / "change-convention.md").read_bytes()
    for skill in ("ingest", "extract-observations"):
        assert (SKILLS / skill / "reference" / "change-convention.md").read_bytes() == charter, skill
    assert CONVENTION_002.read_bytes() == charter
    text = charter.decode()
    assert "`tag`" in text and "2026-11-12 · O-012 · tag · added Q-006 · -" in text
    seed = (PACKAGE_ASSETS / "seed" / "60-log" / "changelog.md").read_text()
    assert "remove-content · tag`" in seed and "`remove-content` and `tag`)" in seed
    assert seed.rstrip().endswith("No changes yet.")


def test_refresh_from_040_adds_extract_observations(tmp_path, git_env):
    old_skills = {}
    for skill in ("charter", "ingest"):
        folder = SKILLS / skill
        old_skills[skill] = {p.relative_to(folder).as_posix(): p.read_text() for p in folder.rglob("*")
                             if p.is_file() and "__pycache__" not in p.parts}
    old = fixture_assets(tmp_path, "0.4.0", name="v4", skills=old_skills, bundled_skills=False)
    old_template = Path(old["CAIRN_ASSETS_DIR"]) / "templates" / "observation.md"
    text = old_template.read_text()
    text = re.sub(r"^(speaker|passage_kind|translated):.*\n", "", text, flags=re.M)
    text = text.split("---\n\n")[0] + "---\n\nOne claim, from one source, with no interpretation.\n"
    old_template.write_text(text)
    eng = init(tmp_path, git_env, old)
    assert not (eng / ".claude" / "skills" / "extract-observations").exists()
    assert "passage_kind" not in (eng / "_templates" / "observation.md").read_text()
    result = run_cairn("refresh", cwd=eng, env=git_env)
    assert result.returncode == 0, result.stderr
    assert "framework 0.4.0 → 0.5.0" in result.stdout
    for rel in SKILL_FILES:
        copied = eng / ".claude" / "skills" / "extract-observations" / rel
        assert copied.read_bytes() == (SKILL_DIR / rel).read_bytes(), rel
    assert (eng / "_templates" / "observation.md").read_bytes() == \
        (PACKAGE_ASSETS / "templates" / "observation.md").read_bytes()
    settings = json.loads((eng / ".claude" / "settings.json").read_text())
    assert "Bash(python3 *observe.py*)" in settings["permissions"]["allow"]


# --- SKILL.md shape (T059) -------------------------------------------------------------------------


def _never_rules(text: str) -> list:
    section = text.split("## Never", 1)[1]
    section = re.split(r"\n## ", section, maxsplit=1)[0]
    rules = re.findall(r"^\d+\. (.*?)(?=^\d+\. |\Z)", section, re.S | re.M)
    return [" ".join(rule.split()) for rule in rules]


def _summary_block(text: str) -> str:
    return re.search(r"```text\n(Extract observations — .*?)```", text, re.S).group(1)


def test_skill_md_size_and_references():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert len(text.splitlines()) <= 250
    refs = set(re.findall(r"reference/[\w-]+\.md", text))
    assert "reference/writing-observations.md" in refs
    for ref in refs:
        assert (SKILL_DIR / ref).is_file(), ref


def test_never_rules_match_contract():
    contract = _never_rules((CONTRACTS / "extract-observations-skill.md").read_text())
    skill = _never_rules((SKILL_DIR / "SKILL.md").read_text())
    assert len(contract) == 8
    assert skill == contract


def test_end_summary_matches_contract():
    contract = _summary_block((CONTRACTS / "extract-observations-skill.md").read_text())
    skill = _summary_block((SKILL_DIR / "SKILL.md").read_text())
    assert skill == contract


def test_skill_names_every_command_and_exit_code():
    text = (SKILL_DIR / "SKILL.md").read_text()
    for command in ("status", "prepare", "add", "progress", "tag", "verify"):
        assert f"`{command}" in text, command
    for phrase in ("cairn init", "/charter", "policy-unconfirmed", "--confirmed", "accept_warnings",
                   "<!-- cairn:content:start -->", "progress S-ID --stopped-at"):
        assert phrase in text, phrase
