import re
from pathlib import Path

import pytest
import yaml

from cairn import layout
from conftest import PACKAGE_ASSETS

STANDARD_FIELDS = (
    "id", "type", "title", "status", "origin", "confidence", "confidence_reason",
    "inference_confirmed", "audience", "supports", "contradicts", "derived_from",
    "supersedes", "clarifies", "created",
)
EXTRA_FIELDS = {
    "source": ("source_type", "raw_file", "provided_by", "source_date", "extraction_method",
               "derived", "restricted", "uncertain_passages"),
    "observation": ("source", "locator", "questions", "derived"),
    "question": ("priority", "raised_by", "hypotheses"),
    "hypothesis": ("question", "supported_by", "contradicted_by"),
    "assumption": ("basis", "questions"),
    "research": ("question", "research_type", "citations"),
    "finding": ("so_what", "supported_by", "contradicted_by", "questions"),
    "issue": ("supported_by", "contradicted_by"),
    "opportunity": ("supported_by", "contradicted_by"),
    "option": ("addresses", "supported_by", "contradicted_by", "lessons_checked"),
    "decision": ("decides", "outcome", "rationale", "decided_by", "decided_on"),
    "lesson": ("polarity", "learned_from", "anonymized", "share_approved"),
}
ENTRY_FORM = {"question", "hypothesis", "assumption", "decision", "lesson"}
REAL_ID = re.compile(r"\b[SOQHARFIPXDL]-\d{3}\b")


def build_correct_tree(root: Path) -> None:
    for rel in layout.CANONICAL_FOLDERS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel in layout.SEED_FILES:
        text = "# Readme\n" if rel == "README.md" else "---\ntype: seed\n---\n\n# Seed\n"
        (root / rel).write_text(text)


def test_counts_and_unique_prefixes():
    assert len(layout.CANONICAL_FOLDERS) == 16
    assert len(layout.SEED_FILES) == 12
    assert len(layout.TEMPLATES) == 12
    assert len({prefix for _, prefix, _ in layout.TEMPLATES}) == 12


def test_canonical_folders_parent_before_child():
    seen = set()
    for rel in layout.CANONICAL_FOLDERS:
        parent = rel.rpartition("/")[0]
        assert not parent or parent in seen
        seen.add(rel)


def test_parse_version():
    assert layout.parse_version("0.2.0") > layout.parse_version("0.1.9")
    assert layout.parse_version("1.0.0-rc1") == (1, 0, 0)
    assert layout.parse_version("1.2.3+build.5") == (1, 2, 3)


def test_check_layout_correct_tree(tmp_path):
    build_correct_tree(tmp_path)
    assert layout.check_layout(tmp_path) == []


def test_check_layout_missing_folder(tmp_path):
    build_correct_tree(tmp_path)
    (tmp_path / "70-views").rmdir()
    assert layout.check_layout(tmp_path) == ["missing folder: 70-views"]


def test_check_layout_extra_folder(tmp_path):
    build_correct_tree(tmp_path)
    (tmp_path / "40-synthesis" / "recommendations").mkdir()
    assert layout.check_layout(tmp_path) == ["extra folder: 40-synthesis/recommendations"]


def test_check_layout_missing_seed(tmp_path):
    build_correct_tree(tmp_path)
    (tmp_path / "60-log" / "lessons.md").unlink()
    assert layout.check_layout(tmp_path) == ["missing seed file: 60-log/lessons.md"]


def test_check_layout_numbered_object(tmp_path):
    build_correct_tree(tmp_path)
    (tmp_path / "30-observations" / "obs.md").write_text("---\nid: O-001\n---\n")
    problems = layout.check_layout(tmp_path)
    assert problems == ["numbered object in a fresh engagement: 30-observations/obs.md"]
    assert layout.check_layout(tmp_path, fresh=False) == []


def test_check_layout_missing_front_matter(tmp_path):
    build_correct_tree(tmp_path)
    (tmp_path / "60-log" / "changelog.md").write_text("# Changelog\n")
    assert layout.check_layout(tmp_path) == ["no front matter: 60-log/changelog.md"]


def test_check_layout_ignores_dot_folders(tmp_path):
    build_correct_tree(tmp_path)
    for dot in (".git/objects", ".claude/skills/x", ".cairn"):
        (tmp_path / dot).mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "x" / "SKILL.md").write_text("O-001")
    assert layout.check_layout(tmp_path) == []


def test_assets_root_honors_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CAIRN_ASSETS_DIR", str(tmp_path))
    assert layout.assets_root() == tmp_path
    monkeypatch.delenv("CAIRN_ASSETS_DIR")
    assert layout.assets_root() == PACKAGE_ASSETS


def test_framework_version_honors_env(monkeypatch):
    monkeypatch.setenv("CAIRN_FRAMEWORK_VERSION", "9.9.9")
    assert layout.framework_version() == "9.9.9"


def test_package_assets_complete():
    assert layout.missing_assets(PACKAGE_ASSETS) == []


# --- Template assets (T015) ---------------------------------------------------


def template_fields(type_: str, text: str) -> dict:
    if type_ in ENTRY_FORM:
        match = re.search(r"```yaml\n(.*?)```", text, re.S)
        assert match, f"{type_}: no fenced yaml block"
        return yaml.safe_load(match.group(1))
    assert text.startswith("---\n"), f"{type_}: no front matter"
    return yaml.safe_load(text.split("---\n")[1])


@pytest.mark.parametrize("type_,prefix,name", layout.TEMPLATES)
def test_template_asset(type_, prefix, name):
    text = (PACKAGE_ASSETS / "templates" / name).read_text()
    fields = template_fields(type_, text)
    for field in STANDARD_FIELDS + EXTRA_FIELDS[type_]:
        assert field in fields, f"{name}: missing {field}"
    assert fields["status"] == "proposed"
    assert fields["audience"] == "internal"
    assert fields["inference_confirmed"] is False
    assert fields["type"] == type_
    assert fields["id"] == f"{prefix}-###"
    if type_ in ENTRY_FORM:
        assert text.startswith(f"## {prefix}-###: ")
    assert not REAL_ID.search(text)


def test_seed_assets_have_no_real_ids():
    for path in (PACKAGE_ASSETS / "seed").rglob("*.md"):
        assert not REAL_ID.search(path.read_text()), path


def test_framework_files_skip_bytecode_caches(tmp_path):
    skill = tmp_path / "skills" / "demo"
    (skill / "scripts" / "__pycache__").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\n---\n")
    (skill / "scripts" / "run.py").write_text("print(1)\n")
    (skill / "scripts" / "__pycache__" / "run.cpython-39.pyc").write_bytes(b"\0")
    for _, _, name in layout.TEMPLATES:
        (tmp_path / "templates").mkdir(exist_ok=True)
        (tmp_path / "templates" / name).write_text("x")
    skill_files = [rel for rel in layout.framework_files(tmp_path) if rel.startswith(".claude/")]
    assert skill_files == [".claude/skills/demo/SKILL.md", ".claude/skills/demo/scripts/run.py"]
