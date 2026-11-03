import ast
import os
from pathlib import Path

import pytest

import cairn
from cairn import safety
from cairn.report import CairnError


def make_pyproject(folder: Path, name: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n')
    return folder


def make_engagement(folder: Path, *, manifest_only=False) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    if manifest_only:
        (folder / ".cairn").mkdir()
        (folder / ".cairn" / "manifest.json").write_text("{}")
    else:
        (folder / "engagement.md").write_text("---\ntype: engagement\n---\n")
    return folder


def test_refuses_inside_framework_repo(tmp_path):
    repo = make_pyproject(tmp_path / "repo", "cairn")
    with pytest.raises(CairnError, match="inside the Cairn framework repository"):
        safety.check_not_in_framework(repo / "sub" / "eng")


def test_accepts_other_project(tmp_path):
    other = make_pyproject(tmp_path / "other", "other")
    safety.check_not_in_framework(other / "eng")


def test_refuses_running_package_project_root():
    root = next(p for p in Path(cairn.__file__).resolve().parents if (p / "pyproject.toml").exists())
    target = root / "does-not-exist" / "eng"
    with pytest.raises(CairnError, match="framework repository"):
        safety.check_not_in_framework(target)
    assert not target.parent.exists()


def test_refuses_nested_engagement_record(tmp_path):
    eng = make_engagement(tmp_path / "eng")
    with pytest.raises(CairnError, match="inside another engagement"):
        safety.check_not_nested(eng / "20-research" / "new", merge=False)


def test_refuses_nested_manifest(tmp_path):
    eng = make_engagement(tmp_path / "eng", manifest_only=True)
    with pytest.raises(CairnError, match="inside another engagement"):
        safety.check_not_nested(eng / "x", merge=False)


def test_engagement_md_of_other_type_is_not_an_engagement(tmp_path):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "engagement.md").write_text("---\ntype: memo\n---\n")
    safety.check_not_nested(folder / "x", merge=False)


def test_merge_into_engagement_points_to_refresh(tmp_path):
    eng = make_engagement(tmp_path / "eng")
    with pytest.raises(CairnError) as err:
        safety.check_not_nested(eng, merge=True)
    assert "cairn refresh" in err.value.hint


def test_target_empty_refuses_non_empty(tmp_path):
    target = tmp_path / "acme-x"
    target.mkdir()
    for n in range(12):
        (target / f"f{n:02}.txt").write_text("x")
    with pytest.raises(CairnError) as err:
        safety.check_target_empty(target, merge=False, engagement_id="acme-x")
    listed = [line for line in err.value.message.splitlines() if line.startswith("  f")]
    assert len(listed) == 10
    assert "acme-x-2" in err.value.hint


def test_target_empty_accepts(tmp_path):
    safety.check_target_empty(tmp_path / "missing", merge=False, engagement_id="x")
    (tmp_path / "empty").mkdir()
    safety.check_target_empty(tmp_path / "empty", merge=False, engagement_id="x")
    (tmp_path / "full").mkdir()
    (tmp_path / "full" / "a").write_text("x")
    safety.check_target_empty(tmp_path / "full", merge=True, engagement_id="x")


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permissions")
def test_writable_refuses_read_only_parent(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o555)
    try:
        with pytest.raises(CairnError, match="not writable"):
            safety.check_writable(ro / "eng")
    finally:
        ro.chmod(0o755)


def test_assets_lists_missing(tmp_path):
    (tmp_path / "seed").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "skills" / "broken").mkdir(parents=True)
    with pytest.raises(CairnError) as err:
        safety.check_assets(tmp_path)
    for expected in ("seed/README.md", "seed/60-log/changelog.md", "templates/finding.md",
                     "skills/broken/SKILL.md"):
        assert expected in err.value.message


# --- FR-018 / R10: static checks over the package source ----------------------

NETWORK_MODULES = {"socket", "urllib", "http", "ftplib", "smtplib", "ssl"}
SOURCE_FILES = sorted(Path(cairn.__file__).parent.rglob("*.py"))


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.name)
def test_no_network_or_remote(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            names = []
        for name in names:
            assert name.split(".")[0] not in NETWORK_MODULES, f"{path.name} imports {name}"
        if isinstance(node, (ast.List, ast.Tuple)):
            # git argument lists: never a network command, never `remote add`
            args = {e.value for e in node.elts if isinstance(e, ast.Constant)}
            assert not args & {"push", "fetch", "pull", "clone"}, path.name
            assert not {"remote", "add"} <= args, path.name
        if isinstance(node, ast.Attribute):
            assert node.attr not in ("symlink", "symlink_to"), path.name
