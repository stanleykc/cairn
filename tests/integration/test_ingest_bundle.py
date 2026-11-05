"""The `ingest` skill ships with the framework (003 FR-001) and the data model moved with it."""

import json
import re
from pathlib import Path

import yaml

from cairn import layout
from conftest import ACME_ID, INIT_ACME, PACKAGE_ASSETS, fixture_assets, run_cairn

SKILL_DIR = PACKAGE_ASSETS / "skills" / "ingest"
CHARTER_DIR = PACKAGE_ASSETS / "skills" / "charter"
SKILL_FILES = (
    "SKILL.md",
    "reference/formats.md",
    "reference/source-record.md",
    "reference/review-and-correct.md",
    "reference/change-convention.md",
    "scripts/ingest.py",
)
REPO = Path(__file__).resolve().parents[2]
CONTRACTS = REPO / "specs" / "003-ingest-skill" / "contracts"
CONVENTION_002 = REPO / "specs" / "002-charter-skill" / "contracts" / "change-convention.md"
DESCRIPTION = (
    "Turn client documents, meeting transcripts and meeting notes in 10-sources/raw/ (PDF, Word, "
    "markdown, text, VTT, SRT) into cited, verbatim source files, respecting the engagement's "
    "model-use policy. Use when new material arrives, or to review and approve extracted sources."
)
ARGUMENT_HINT = "[file(s) in 10-sources/raw/, or 'review' …] [context: who provided it, when, why it matters]"
TEMPLATE_FIELDS = (
    "material", "source_type", "raw_file", "raw_sha256", "raw_bytes", "provided_by", "source_date",
    "meeting_title", "meeting_date", "attendees", "author", "author_kind", "extraction_status",
    "fidelity", "extraction_method", "derived", "restricted", "content_removed", "page_count",
    "pages_reviewed", "uncertain_passages",
)
EXTENSIONS = (".pdf", ".docx", ".md", ".markdown", ".txt", ".vtt", ".srt")


def skill_front_matter() -> dict:
    return yaml.safe_load((SKILL_DIR / "SKILL.md").read_text().split("---\n")[1])


def init(tmp_path, git_env, env_extra=None) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    result = run_cairn(*INIT_ACME, "--no-git", cwd=work, env=git_env | (env_extra or {}))
    assert result.returncode == 0, result.stderr
    return work / ACME_ID


def test_init_ships_ingest(tmp_path, git_env):
    eng = init(tmp_path, git_env)
    manifest = json.loads((eng / ".cairn" / "manifest.json").read_text())
    for rel in SKILL_FILES:
        copied = eng / ".claude" / "skills" / "ingest" / rel
        assert copied.is_file() and not copied.is_symlink(), rel
        assert copied.read_bytes() == (SKILL_DIR / rel).read_bytes(), rel
        assert f".claude/skills/ingest/{rel}" in manifest["files"], rel
    settings = json.loads((eng / ".claude" / "settings.json").read_text())
    assert "Bash(python3 *ingest.py*)" in settings["permissions"]["allow"]
    readme = (eng / "README.md").read_text()
    assert f"- `ingest` — {DESCRIPTION}" in readme


def test_skill_front_matter():
    meta = skill_front_matter()
    assert meta == {
        "name": "ingest",
        "description": DESCRIPTION,
        "argument-hint": ARGUMENT_HINT,
        "allowed-tools": "Read, Edit, Write, Bash(python3 *ingest.py*)",
    }
    assert ("ingest", DESCRIPTION) in layout.bundled_skills(PACKAGE_ASSETS)


def test_no_placeholder_files_in_skill():
    names = [p.name for p in SKILL_DIR.rglob("*") if p.is_file()]
    assert ".gitkeep" not in names
    shipped = {rel.split("/ingest/", 1)[1] for rel in layout.framework_files(PACKAGE_ASSETS)
               if rel.startswith(".claude/skills/ingest/")}
    assert shipped == set(SKILL_FILES)


def test_template_has_source_fields():
    text = (PACKAGE_ASSETS / "templates" / "source.md").read_text()
    front = yaml.safe_load(text.split("---\n")[1])
    for field in TEMPLATE_FIELDS:
        assert field in front, field
    assert front["extraction_status"] == "in-progress" and front["fidelity"] == "pending"
    body = text.split("---\n", 2)[2]
    headings = re.findall(r"^## (.+)$", body, re.M)
    assert headings == ["Context", "Description", "Speakers", "Uncertain passages", "Extracted content"]
    assert body.count("<!-- cairn:content:start -->") == 1 and body.count("<!-- cairn:content:end -->") == 1
    assert body.index("<!-- cairn:content:start -->") < body.index("<!-- cairn:content:end -->")


def test_change_convention_copies_identical():
    charter = (CHARTER_DIR / "reference" / "change-convention.md").read_bytes()
    assert (SKILL_DIR / "reference" / "change-convention.md").read_bytes() == charter
    assert CONVENTION_002.read_bytes() == charter
    text = charter.decode()
    for event in ("extraction-fix", "restrict", "remove-content"):
        assert f"`{event}`" in text
    assert "`<ID> @ <locator>`" in text


def test_refresh_from_020_adds_ingest(tmp_path, git_env):
    charter = {rel.relative_to(CHARTER_DIR).as_posix(): rel.read_text()
               for rel in CHARTER_DIR.rglob("*") if rel.is_file() and "__pycache__" not in rel.parts}
    old = fixture_assets(tmp_path, "0.2.0", name="v2", skills={"charter": charter}, bundled_skills=False)
    old_template = Path(old["CAIRN_ASSETS_DIR"]) / "templates" / "source.md"
    old_template.write_text(old_template.read_text().split("material:")[0] + "---\n\n## Summary\n")
    eng = init(tmp_path, git_env, old)
    assert not (eng / ".claude" / "skills" / "ingest").exists()
    result = run_cairn("refresh", cwd=eng, env=git_env)
    assert result.returncode == 0, result.stderr
    assert "framework 0.2.0 → 0.4.0" in result.stdout
    for rel in SKILL_FILES:
        assert (eng / ".claude" / "skills" / "ingest" / rel).read_bytes() == (SKILL_DIR / rel).read_bytes(), rel
    assert (eng / "_templates" / "source.md").read_bytes() == (PACKAGE_ASSETS / "templates" / "source.md").read_bytes()
    settings = json.loads((eng / ".claude" / "settings.json").read_text())
    assert "Bash(python3 *ingest.py*)" in settings["permissions"]["allow"]


# --- T074: SKILL.md shape ----------------------------------------------------------------------


def _never_rules(text: str) -> list:
    section = text.split("## Never", 1)[1]
    section = re.split(r"\n## ", section, maxsplit=1)[0]
    rules = re.findall(r"^\d+\. (.*?)(?=^\d+\. |\Z)", section, re.S | re.M)
    return [" ".join(rule.split()) for rule in rules]


def test_skill_md_size_and_references():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert len(text.splitlines()) <= 250
    refs = set(re.findall(r"reference/[\w-]+\.md", text))
    assert refs >= {"reference/formats.md", "reference/source-record.md", "reference/review-and-correct.md"}
    for ref in refs:
        assert (SKILL_DIR / ref).is_file(), ref


def test_never_rules_match_contract():
    contract = _never_rules((CONTRACTS / "ingest-skill.md").read_text())
    skill = _never_rules((SKILL_DIR / "SKILL.md").read_text())
    assert len(contract) == 10
    assert skill == contract


def test_skill_and_formats_mention_every_extension():
    skill = (SKILL_DIR / "SKILL.md").read_text()
    formats = (SKILL_DIR / "reference" / "formats.md").read_text()
    for ext in EXTENSIONS:
        assert f"`{ext}`" in skill, ext
        assert f"`{ext}`" in formats, ext
