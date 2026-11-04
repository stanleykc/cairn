"""The `charter` skill ships with the framework (FR-001) and the data model moved with it."""

import json
import re
from pathlib import Path

import yaml

from cairn import layout
from conftest import ACME_ID, INIT_ACME, PACKAGE_ASSETS, fixture_assets, run_cairn

SKILL_DIR = PACKAGE_ASSETS / "skills" / "charter"
SKILL_FILES = (
    "SKILL.md",
    "reference/interview.md",
    "reference/formats.md",
    "reference/review-and-revise.md",
    "reference/change-convention.md",
    "scripts/charter.py",
)
REPO = Path(__file__).resolve().parents[2]
CONTRACTS = REPO / "specs" / "002-charter-skill" / "contracts"
DESCRIPTION = (
    "Frame or revise the engagement charter (scope, key questions, hypotheses, assumptions, "
    "stakeholders, lenses) by interviewing the consultant. Use at kickoff, or when the weekly "
    "steer changes questions, hypotheses or scope. Never reads client documents."
)


def skill_front_matter() -> dict:
    return yaml.safe_load((SKILL_DIR / "SKILL.md").read_text().split("---\n")[1])


def init(tmp_path, git_env, env_extra=None) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    result = run_cairn(*INIT_ACME, "--no-git", cwd=work, env=git_env | (env_extra or {}))
    assert result.returncode == 0, result.stderr
    return work / ACME_ID


def test_init_ships_charter(tmp_path, git_env):
    eng = init(tmp_path, git_env)
    manifest = json.loads((eng / ".cairn" / "manifest.json").read_text())
    for rel in SKILL_FILES:
        copied = eng / ".claude" / "skills" / "charter" / rel
        assert copied.is_file() and not copied.is_symlink(), rel
        assert copied.read_bytes() == (SKILL_DIR / rel).read_bytes(), rel
        assert f".claude/skills/charter/{rel}" in manifest["files"], rel
    readme = (eng / "README.md").read_text()
    assert f"- `charter` — {DESCRIPTION}" in readme


def test_skill_front_matter():
    meta = skill_front_matter()
    assert meta["name"] == "charter"
    assert meta["description"] == DESCRIPTION
    assert meta["argument-hint"]
    assert meta["allowed-tools"] == "Read, Edit, Write, Bash(python3 *charter.py *)"
    assert layout.bundled_skills(PACKAGE_ASSETS) == [("charter", DESCRIPTION)]


def test_no_placeholder_files_in_skill():
    names = [p.name for p in SKILL_DIR.rglob("*") if p.is_file()]
    assert ".gitkeep" not in names
    shipped = {rel.split("/charter/", 1)[1] for rel in layout.framework_files(PACKAGE_ASSETS)
               if rel.startswith(".claude/skills/charter/")}
    assert shipped == set(SKILL_FILES)


def test_refresh_adds_charter_to_010_engagement(tmp_path, git_env):
    old = fixture_assets(tmp_path, "0.1.0", name="v1", bundled_skills=False)
    eng = init(tmp_path, git_env, old)
    assert not (eng / ".claude").exists()
    result = run_cairn("refresh", cwd=eng, env=git_env)
    assert result.returncode == 0, result.stderr
    assert "framework 0.1.0 → 0.2.0" in result.stdout
    for rel in SKILL_FILES:
        assert (eng / ".claude" / "skills" / "charter" / rel).read_bytes() == (SKILL_DIR / rel).read_bytes()
    for _, _, name in layout.TEMPLATES:
        assert (eng / "_templates" / name).read_bytes() == (PACKAGE_ASSETS / "templates" / name).read_bytes()


def template_fields(name: str) -> dict:
    text = (PACKAGE_ASSETS / "templates" / name).read_text()
    match = re.search(r"```yaml\n(.*?)```", text, re.S)
    block = match.group(1) if match else text.split("---\n")[1]
    return yaml.safe_load(block)


def test_templates_carry_change_fields():
    for _, _, name in layout.TEMPLATES:
        fields = template_fields(name)
        assert fields["change_reason"] == "", name
        assert fields["change_trigger"] == "", name
        keys = list(fields)
        assert keys.index("change_reason") == keys.index("clarifies") + 1, name
    hypothesis = template_fields("hypothesis.md")
    assert hypothesis["confirm_if"] == "" and hypothesis["reject_if"] == ""
    keys = list(hypothesis)
    assert keys.index("confirm_if") == keys.index("question") + 1


def test_seed_files_carry_new_fields(tmp_path, git_env):
    eng = init(tmp_path, git_env)
    record = yaml.safe_load((eng / "engagement.md").read_text().split("---\n")[1])
    assert record["model_use_notes"] == ""
    scope_text = (eng / "00-charter" / "scope.md").read_text()
    scope = yaml.safe_load(scope_text.split("---\n")[1])
    assert scope["model_use_notes"] == ""
    assert scope["charter_status"] == "draft"
    assert scope["approved_on"] == "" and scope["approved_by"] == ""
    for heading in ("### In scope", "### Out of scope", "## Constraints"):
        assert f"\n{heading}\n" in scope_text
    assert "Current policy: **unconfirmed**.\nRestrictions: none recorded.\n" in scope_text
    changelog = (eng / "60-log" / "changelog.md").read_text()
    assert "approve-charter" in changelog and changelog.rstrip().endswith("No changes yet.")


def test_change_convention_copy_is_identical():
    shipped = SKILL_DIR / "reference" / "change-convention.md"
    assert shipped.read_bytes() == (CONTRACTS / "change-convention.md").read_bytes()


def test_skill_md_size_and_references():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert len(text.splitlines()) <= 250
    for ref in set(re.findall(r"reference/[\w-]+\.md", text)):
        assert (SKILL_DIR / ref).is_file(), ref


def _never_rules(text: str) -> list:
    section = text.split("## Never", 1)[1]
    section = re.split(r"\n## ", section, maxsplit=1)[0]
    rules = re.findall(r"^\d\. (.*?)(?=^\d\. |\Z)", section, re.S | re.M)
    return [" ".join(rule.split()) for rule in rules]


def test_never_rules_match_contract():
    contract = _never_rules((CONTRACTS / "charter-skill.md").read_text())
    skill = _never_rules((SKILL_DIR / "SKILL.md").read_text())
    assert len(contract) == 9
    assert skill == contract
