import json
import os
import time
from pathlib import Path

import pytest

from cairn import refresh_cmd
from cairn.report import CairnError
from conftest import ACME_ID, INIT_ACME, fixture_assets, run_cairn, tree_hash

ALPHA = {"SKILL.md": "---\nname: alpha\ndescription: \"Alpha\"\n---\n", "scripts/a.py": "a = 1\n"}
GAMMA = {"SKILL.md": "---\nname: gamma\ndescription: \"Gamma\"\n---\n"}
BETA = {"SKILL.md": "---\nname: beta\ndescription: \"Beta\"\n---\n"}

FRAMEWORK_AREAS = ("_templates", ".claude/skills", ".cairn", "engagement.md")
CONTENT_FOLDERS = (
    "_inbox", "10-sources/raw", "10-sources/extracted", "20-research", "30-observations",
    "40-synthesis/findings", "40-synthesis/issues", "40-synthesis/opportunities",
    "50-options", "70-views", "80-deliverables",
)


class Setup:
    def __init__(self, tmp_path: Path, git_env: dict):
        self.tmp = tmp_path
        self.v1 = git_env | fixture_assets(
            tmp_path, "0.1.0", {"alpha": ALPHA, "gamma": GAMMA}, "v1", bundled_skills=False
        )
        self.v2 = git_env | fixture_assets(tmp_path, "0.2.0", {"beta": BETA}, "v2", bundled_skills=False)
        finding = Path(self.v2["CAIRN_ASSETS_DIR"]) / "templates" / "finding.md"
        finding.write_text(finding.read_text() + "\n## Next steps\n")
        self.work = tmp_path / "work"
        self.work.mkdir()
        result = run_cairn(*INIT_ACME, "--no-git", cwd=self.work, env=self.v1)
        assert result.returncode == 0, result.stderr
        self.eng = self.work / ACME_ID
        for rel in CONTENT_FOLDERS:
            (self.eng / rel / "sample.md").write_text(f"sample in {rel}\n")
        with open(self.eng / "00-charter" / "questions.md", "a") as fh:
            fh.write("\nconsultant notes\n")
        with open(self.eng / "60-log" / "decisions.md", "a") as fh:
            fh.write("\nconsultant notes\n")

    def refresh(self, *args, env=None):
        return run_cairn("refresh", *args, cwd=self.eng, env=env or self.v2)

    def content_hash(self):
        return tree_hash(self.eng, exclude=FRAMEWORK_AREAS)

    def manifest(self):
        return json.loads((self.eng / ".cairn" / "manifest.json").read_text())

    def edit(self, rel, text="consultant edit\n"):
        path = self.eng / rel
        path.write_text(path.read_text() + text)
        return path.read_bytes()


@pytest.fixture
def s(tmp_path, git_env):
    return Setup(tmp_path, git_env)


def test_update_add_keep_edited(s):
    edited = s.edit("_templates/observation.md")
    record_before = (s.eng / "engagement.md").read_text().splitlines()
    content_before = s.content_hash()

    result = s.refresh()
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert f"Refreshed {ACME_ID}: framework 0.1.0 → 0.2.0" in out
    assert "updated: _templates/finding.md" in out
    assert ".claude/skills/beta/SKILL.md" in out.split("added:")[1].splitlines()[0]
    assert "kept (edited, not replaced): _templates/observation.md" in out
    assert 'git commit -m "Refresh Cairn to 0.2.0"' in out

    v2 = Path(s.v2["CAIRN_ASSETS_DIR"])
    assert (s.eng / "_templates/finding.md").read_bytes() == (v2 / "templates/finding.md").read_bytes()
    assert (s.eng / ".claude/skills/beta/SKILL.md").read_text() == BETA["SKILL.md"]
    assert (s.eng / "_templates/observation.md").read_bytes() == edited

    record_after = (s.eng / "engagement.md").read_text().splitlines()
    diff = [(a, b) for a, b in zip(record_before, record_after) if a != b]
    assert diff == [(
        'framework_version: "0.1.0"  # updated only by cairn refresh',
        'framework_version: "0.2.0"  # updated only by cairn refresh',
    )]
    assert s.manifest()["framework_version"] == "0.2.0"
    assert s.content_hash() == content_before  # SC-004, FR-023


def test_replace_edited(s):
    edited = s.edit("_templates/observation.md")
    result = s.refresh("--replace-edited")
    assert result.returncode == 0, result.stderr
    backups = list((s.eng / ".cairn" / "backups").iterdir())
    assert len(backups) == 1
    assert len(backups[0].name) == len("YYYYMMDD-HHMMSS")
    assert (backups[0] / "_templates" / "observation.md").read_bytes() == edited
    v2 = Path(s.v2["CAIRN_ASSETS_DIR"])
    assert (s.eng / "_templates/observation.md").read_bytes() == (
        v2 / "templates/observation.md"
    ).read_bytes()
    assert "backed up: .cairn/backups/" in result.stdout


def use_env(monkeypatch, env):
    for key in ("CAIRN_ASSETS_DIR", "CAIRN_FRAMEWORK_VERSION"):
        monkeypatch.setenv(key, env[key])


def test_tty_confirm(s, monkeypatch):
    obs = s.edit("_templates/observation.md")
    s.edit("_templates/option.md")
    use_env(monkeypatch, s.v2)
    asked = []

    def confirm(rel):
        asked.append(rel)
        return rel == "_templates/option.md"

    report = refresh_cmd.run(s.eng, confirm=confirm)
    assert sorted(asked) == ["_templates/observation.md", "_templates/option.md"]
    assert report.kept_edited == ["_templates/observation.md"]
    assert "_templates/option.md" in report.updated
    assert (s.eng / "_templates/observation.md").read_bytes() == obs
    assert len(report.backed_up) == 1 and report.backed_up[0].endswith("_templates/option.md")
    # The kept file keeps its old manifest hash, so the next refresh still sees it as edited.
    second = refresh_cmd.run(s.eng, confirm=lambda rel: False)
    assert second.kept_edited == ["_templates/observation.md"]


def test_remove(s):
    s.edit(".claude/skills/gamma/SKILL.md")
    result = s.refresh()
    assert result.returncode == 0, result.stderr
    assert not (s.eng / ".claude/skills/alpha").exists()  # dropped and unchanged: removed
    assert "removed: .claude/skills/alpha/SKILL.md, .claude/skills/alpha/scripts/a.py" in result.stdout
    assert (s.eng / ".claude/skills/gamma/SKILL.md").exists()  # dropped but edited: kept
    assert ".claude/skills/gamma/SKILL.md" in result.stdout.split("kept (edited, not replaced):")[1]
    files = s.manifest()["files"]
    assert not any(p.startswith((".claude/skills/alpha/", ".claude/skills/gamma/")) for p in files)


def test_deleted_framework_file_readded(s):
    (s.eng / "_templates" / "lesson.md").unlink()
    result = s.refresh(env=s.v1)
    assert result.returncode == 0, result.stderr
    assert (s.eng / "_templates" / "lesson.md").is_file()
    assert "added:   _templates/lesson.md" in result.stdout


def test_existing_unlisted_path_treated_as_edited(s):
    mine = s.eng / ".claude/skills/beta/SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("my own beta\n")
    result = s.refresh()
    assert result.returncode == 0, result.stderr
    assert mine.read_text() == "my own beta\n"
    assert ".claude/skills/beta/SKILL.md" in result.stdout.split("kept (edited, not replaced):")[1]


def test_consultant_skill_untouched(s):
    mine = s.eng / ".claude/skills/my-own/SKILL.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("---\nname: my-own\n---\n")
    before = mine.read_bytes()
    assert s.refresh().returncode == 0
    assert mine.read_bytes() == before
    assert ".claude/skills/my-own/SKILL.md" not in s.manifest()["files"]


def test_newer_engagement_refused(s):
    assert s.refresh().returncode == 0
    before = tree_hash(s.eng)
    result = s.refresh(env=s.v1)
    assert result.returncode == 1
    assert "0.2.0" in result.stderr and "0.1.0" in result.stderr
    assert tree_hash(s.eng) == before


def test_not_an_engagement(s):
    result = run_cairn("refresh", s.work, cwd=s.tmp, env=s.v2)
    assert result.returncode == 1
    assert "not a Cairn engagement" in result.stderr


def test_missing_manifest(s):
    (s.eng / ".cairn" / "manifest.json").unlink()
    before = tree_hash(s.eng)
    result = s.refresh()
    assert result.returncode == 1
    assert "manifest" in result.stderr
    assert tree_hash(s.eng) == before


def test_nothing_to_change(s):
    assert s.refresh().returncode == 0
    before = tree_hash(s.eng)
    result = s.refresh()
    assert result.returncode == 0
    assert "nothing to change" in result.stdout
    assert tree_hash(s.eng) == before


def test_rollback(s, monkeypatch):
    s.edit("_templates/observation.md")
    use_env(monkeypatch, s.v2)
    before = tree_hash(s.eng, exclude=(".cairn/backups",))
    real_replace = os.replace
    calls = {"n": 0}

    def failing_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("injected")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(CairnError, match="refresh failed: injected; restored original files"):
        refresh_cmd.run(s.eng, replace_edited=True)
    assert tree_hash(s.eng, exclude=(".cairn/backups",)) == before
    backups = list((s.eng / ".cairn" / "backups").rglob("observation.md"))
    assert len(backups) == 1  # backups are never deleted
    assert not list(s.eng.rglob("*.cairn-tmp"))


def test_refresh_is_fast(s):
    start = time.monotonic()
    assert s.refresh().returncode == 0
    assert time.monotonic() - start < 2.0
