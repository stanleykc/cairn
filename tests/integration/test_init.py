import builtins
import json
import re
import time
from datetime import date
from pathlib import Path

import pytest
import yaml

from cairn import cli, layout
from cairn.textutil import sha256_bytes
from conftest import (
    ACME, ACME_ID, FULFILLMENT, INIT_ACME, LEAD, PACKAGE_ASSETS, fixture_assets, run_cairn,
)

REAL_ID = re.compile(r"\b[SOQHARFIPXDL]-[0-9]{3}\b")
TODAY = date.today().isoformat()


def front_matter(path: Path) -> dict:
    return yaml.safe_load(path.read_text().split("---\n")[1])


@pytest.fixture
def acme(tmp_path, git_env) -> Path:
    result = run_cairn(*INIT_ACME, "--no-git", cwd=tmp_path, env=git_env)
    assert result.returncode == 0, result.stderr
    return tmp_path / ACME_ID


def test_layout(acme):
    assert acme.is_dir()
    assert layout.check_layout(acme) == []


def test_seed_files(acme):
    for rel in layout.SEED_FILES:
        assert (acme / rel).is_file(), rel
    for md in acme.rglob("*.md"):
        rel = md.relative_to(acme).as_posix()
        if rel == "README.md" or rel.startswith(("_templates/", ".claude/")):
            continue
        assert isinstance(front_matter(md), dict), rel
    holds = {
        "00-charter/questions.md": "question",
        "00-charter/hypotheses.md": "hypothesis",
        "00-charter/assumptions.md": "assumption",
        "60-log/decisions.md": "decision",
        "60-log/lessons.md": "lesson",
    }
    for rel, kind in holds.items():
        meta = front_matter(acme / rel)
        assert meta == {"type": "collection", "holds": kind}, rel


def test_templates(acme):
    names = sorted(p.name for p in (acme / "_templates").iterdir())
    assert names == sorted(name for _, _, name in layout.TEMPLATES)
    for name in names:
        assert (acme / "_templates" / name).read_bytes() == (
            PACKAGE_ASSETS / "templates" / name
        ).read_bytes()


def test_engagement_record(acme):
    meta = front_matter(acme / "engagement.md")
    assert meta == {
        "id": ACME_ID,
        "type": "engagement",
        "engagement_name": FULFILLMENT,
        "client": ACME,
        "client_code_name": "",
        "lead_consultant": LEAD,
        "team": [],
        "start_date": date.today(),
        "created": date.today(),
        "framework_version": "0.3.0",
        "model_use": "unconfirmed",
        "model_use_notes": "",
    }


def test_team_and_start_date(tmp_path, git_env):
    result = run_cairn(
        *INIT_ACME, "--no-git", "--team", "Sam Analyst", "--team", "Lee Analyst",
        "--start-date", "2026-10-01", cwd=tmp_path, env=git_env,
    )
    assert result.returncode == 0, result.stderr
    meta = front_matter(tmp_path / ACME_ID / "engagement.md")
    assert meta["team"] == ["Sam Analyst", "Lee Analyst"]
    assert meta["start_date"] == date(2026, 10, 1)


def test_bad_start_date(tmp_path, git_env):
    result = run_cairn(*INIT_ACME, "--start-date", "01/10/2026", cwd=tmp_path, env=git_env)
    assert result.returncode == 2
    assert not (tmp_path / ACME_ID).exists()


def test_no_numbered_objects(acme):
    for md in acme.rglob("*.md"):
        if md.relative_to(acme).parts[0] == ".claude":
            continue  # skill instructions use example IDs; they are not objects
        assert not REAL_ID.search(md.read_text()), md


def test_manifest(acme):
    manifest = json.loads((acme / ".cairn" / "manifest.json").read_text())
    assert manifest["schema"] == 1
    assert manifest["framework_version"] == "0.3.0"
    expected = {f"_templates/{name}" for _, _, name in layout.TEMPLATES}
    assert {f for f in manifest["files"] if not f.startswith(".claude/")} == expected
    for rel, digest in manifest["files"].items():
        assert digest == sha256_bytes((acme / rel).read_bytes())


def test_slug_from_accents(tmp_path, git_env):
    result = run_cairn(
        "init", "--engagement", "Q4: Fulfillment Review!", "--client", "Société Générale",
        "--lead", LEAD, "--no-git", cwd=tmp_path, env=git_env,
    )
    assert result.returncode == 0, result.stderr
    folder = tmp_path / "societe-generale-q4-fulfillment-review"
    meta = front_matter(folder / "engagement.md")
    assert meta["engagement_name"] == "Q4: Fulfillment Review!"
    assert meta["client"] == "Société Générale"
    assert meta["id"] == "societe-generale-q4-fulfillment-review"


def test_explicit_path(tmp_path, git_env):
    result = run_cairn(*INIT_ACME, "--no-git", "other-name", cwd=tmp_path, env=git_env)
    assert result.returncode == 0, result.stderr
    assert front_matter(tmp_path / "other-name" / "engagement.md")["id"] == "other-name"
    assert not (tmp_path / ACME_ID).exists()


def test_nested_explicit_path_creates_parents(tmp_path, git_env):
    result = run_cairn(*INIT_ACME, "--no-git", "a/b/eng", cwd=tmp_path, env=git_env)
    assert result.returncode == 0, result.stderr
    assert layout.check_layout(tmp_path / "a" / "b" / "eng") == []


def test_summary(tmp_path, git_env):
    result = run_cairn(*INIT_ACME, "--no-git", cwd=tmp_path, env=git_env)
    out = result.stdout
    assert f"Created engagement {ACME_ID} at {tmp_path.resolve() / ACME_ID}" in out
    assert "framework 0.3.0 · 16 folders · 12 seed files · 12 templates · 2 skills" in out
    assert "Model-use policy is UNCONFIRMED" in out
    assert "1. Confirm the client's model-use policy" in out
    assert "2. Run the `charter` skill" in out
    assert "3. Put original files in 10-sources/raw/" in out


def test_missing_engagement_non_tty(tmp_path, git_env):
    result = run_cairn("init", "--client", ACME, "--lead", LEAD, cwd=tmp_path, env=git_env)
    assert result.returncode == 2
    assert "--engagement" in result.stderr
    assert list(tmp_path.iterdir()) == [tmp_path / "gitconfig"]


def queue_input(monkeypatch, answers):
    prompts = []
    queue = list(answers)

    def fake_input(prompt=""):
        prompts.append(prompt)
        answer = queue.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(builtins, "input", fake_input)
    return prompts


@pytest.fixture
def in_process(tmp_path, monkeypatch, git_env):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", git_env["GIT_CONFIG_GLOBAL"])
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return tmp_path


def test_prompts(in_process, monkeypatch):
    prompts = queue_input(monkeypatch, [FULFILLMENT, "", ACME, LEAD, ""])
    assert cli.main(["init", "--no-git"]) == 0
    assert [p.split(" (")[0].split(" [")[0].rstrip(": ") for p in prompts] == [
        "Engagement name", "Client code name", "Client name", "Lead consultant",
        "Model-use policy",
    ]
    assert "[Test Lead]" in prompts[3]
    meta = front_matter(in_process / ACME_ID / "engagement.md")
    assert meta["client"] == ACME
    assert meta["model_use"] == "unconfirmed"


def test_prompts_code_name_blank_client(in_process, monkeypatch):
    queue_input(monkeypatch, ["Pricing Study", "Falcon", "", "", "restricted"])
    assert cli.main(["init", "--no-git"]) == 0
    meta = front_matter(in_process / "falcon-pricing-study" / "engagement.md")
    assert meta["client"] == ""
    assert meta["client_code_name"] == "Falcon"
    assert meta["lead_consultant"] == LEAD  # default from git config
    assert meta["model_use"] == "restricted"


# --- US3: skills -------------------------------------------------------------

DEMO_SKILL = {
    "SKILL.md": '---\nname: demo-skill\ndescription: "Synthetic test skill"\n---\n\n# Demo\n',
    "scripts/check.py": "print('ok')\n",
}


def test_skills_copied(tmp_path, git_env):
    env = git_env | fixture_assets(tmp_path, skills={"demo-skill": DEMO_SKILL})
    work = tmp_path / "work"
    work.mkdir()
    result = run_cairn(*INIT_ACME, "--no-git", cwd=work, env=env)
    assert result.returncode == 0, result.stderr
    eng = work / ACME_ID
    manifest = json.loads((eng / ".cairn" / "manifest.json").read_text())
    for rel, text in DEMO_SKILL.items():
        copied = eng / ".claude" / "skills" / "demo-skill" / rel
        assert copied.is_file() and not copied.is_symlink()
        assert copied.read_text() == text
        assert f".claude/skills/demo-skill/{rel}" in manifest["files"]
    readme = (eng / "README.md").read_text()
    assert "Skills installed when this engagement was created:" in readme
    assert "- `demo-skill` — Synthetic test skill" in readme
    assert "- `charter` — " in readme
    assert "- `ingest` — " in readme
    assert "The current set is in `.claude/skills/`." in readme
    assert "· 3 skills" in result.stdout


def test_no_skills_bundled(tmp_path, git_env):
    env = git_env | fixture_assets(tmp_path, bundled_skills=False)
    work = tmp_path / "work"
    work.mkdir()
    assert run_cairn(*INIT_ACME, "--no-git", cwd=work, env=env).returncode == 0
    acme = work / ACME_ID
    assert not (acme / ".claude").exists()
    readme = (acme / "README.md").read_text()
    assert "None installed yet." in readme
    assert "The current set is in `.claude/skills/`." in readme


def test_framework_version_recorded(tmp_path, git_env):
    env = git_env | fixture_assets(tmp_path, version="0.3.0")
    work = tmp_path / "work"
    work.mkdir()
    result = run_cairn(*INIT_ACME, "--no-git", cwd=work, env=env)
    assert result.returncode == 0, result.stderr
    assert front_matter(work / ACME_ID / "engagement.md")["framework_version"] == "0.3.0"
    manifest = json.loads((work / ACME_ID / ".cairn" / "manifest.json").read_text())
    assert manifest["framework_version"] == "0.3.0"


def test_skills_dir_not_in_layout(tmp_path, git_env):
    env = git_env | fixture_assets(tmp_path, skills={"demo-skill": DEMO_SKILL})
    work = tmp_path / "work"
    work.mkdir()
    assert run_cairn(*INIT_ACME, "--no-git", cwd=work, env=env).returncode == 0
    assert (work / ACME_ID / ".claude" / "skills").is_dir()
    assert layout.check_layout(work / ACME_ID) == []


def test_init_is_fast(tmp_path, git_env):
    start = time.monotonic()
    result = run_cairn(*INIT_ACME, "--no-git", cwd=tmp_path, env=git_env)
    assert result.returncode == 0
    assert time.monotonic() - start < 2.0
