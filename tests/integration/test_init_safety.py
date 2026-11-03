import builtins
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from cairn import cli, init_cmd
from cairn.report import CairnError
from cairn.transaction import Transaction
from conftest import (
    ACME, ACME_ID, FALCON, FULFILLMENT, GLOBEX_CORP, INIT_ACME, LEAD, PRICING,
    fixture_assets, run_cairn, tree_hash,
)


def front_matter(path: Path) -> dict:
    return yaml.safe_load(path.read_text().split("---\n")[1])


@pytest.fixture
def work(tmp_path) -> Path:
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


def test_refuses_inside_framework_repo(work, git_env):
    fake = work / "fake-cairn"
    fake.mkdir()
    (fake / "pyproject.toml").write_text('[project]\nname = "cairn"\n')
    (fake / "src").mkdir()
    before = tree_hash(fake)
    result = run_cairn(*INIT_ACME, cwd=fake / "src", env=git_env)
    assert result.returncode == 1
    assert "inside the Cairn framework repository" in result.stderr
    assert tree_hash(fake) == before
    assert sorted(p.name for p in fake.iterdir()) == ["pyproject.toml", "src"]


def test_refuses_inside_another_engagement(work, git_env):
    assert run_cairn(*INIT_ACME, "--no-git", cwd=work, env=git_env).returncode == 0
    eng = work / ACME_ID
    before = tree_hash(eng)
    result = run_cairn(
        "init", "--engagement", "X", "--client", "Globex", "--lead", LEAD,
        cwd=eng / "20-research", env=git_env,
    )
    assert result.returncode == 1
    assert "inside another engagement" in result.stderr
    assert tree_hash(eng) == before


def test_second_identical_run_refused(work, git_env):
    assert run_cairn(*INIT_ACME, "--no-git", cwd=work, env=git_env).returncode == 0
    before = tree_hash(work)
    result = run_cairn(*INIT_ACME, "--no-git", cwd=work, env=git_env)
    assert result.returncode == 1
    assert "not empty" in result.stderr
    assert "  00-charter\n" in result.stderr
    assert "… and 4 more" in result.stderr
    assert f"{ACME_ID}-2" in result.stderr
    assert tree_hash(work) == before


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permissions")
def test_read_only_parent(work, git_env):
    ro = work / "ro"
    ro.mkdir()
    ro.chmod(0o555)
    try:
        result = run_cairn(*INIT_ACME, ro / "e", cwd=work, env=git_env)
        assert result.returncode == 1
        assert "not writable" in result.stderr
        assert list(ro.iterdir()) == []
    finally:
        ro.chmod(0o755)


def test_missing_template_asset(tmp_path, work, git_env):
    env = git_env | fixture_assets(tmp_path)
    (Path(env["CAIRN_ASSETS_DIR"]) / "templates" / "finding.md").unlink()
    result = run_cairn(*INIT_ACME, cwd=work, env=env)
    assert result.returncode == 1
    assert "templates/finding.md" in result.stderr
    assert list(work.iterdir()) == []


def test_model_use_restricted(work, git_env):
    result = run_cairn(*INIT_ACME, "--no-git", "--model-use", "restricted", cwd=work, env=git_env)
    assert result.returncode == 0, result.stderr
    eng = work / ACME_ID
    assert front_matter(eng / "engagement.md")["model_use"] == "restricted"
    assert front_matter(eng / "00-charter" / "scope.md")["model_use"] == "restricted"
    assert "UNCONFIRMED" not in (eng / "README.md").read_text()


def test_model_use_bogus(work, git_env):
    result = run_cairn(*INIT_ACME, "--model-use", "bogus", cwd=work, env=git_env)
    assert result.returncode == 2
    assert list(work.iterdir()) == []


def test_model_use_default_unconfirmed(work, git_env):
    result = run_cairn(*INIT_ACME, "--no-git", cwd=work, env=git_env)
    eng = work / ACME_ID
    assert front_matter(eng / "engagement.md")["model_use"] == "unconfirmed"
    assert front_matter(eng / "00-charter" / "scope.md")["model_use"] == "unconfirmed"
    assert "model-use policy is UNCONFIRMED" in (eng / "README.md").read_text()
    assert "UNCONFIRMED" in result.stdout


def test_model_use_allowed_no_warning(work, git_env):
    result = run_cairn(*INIT_ACME, "--no-git", "--model-use", "allowed", cwd=work, env=git_env)
    assert "UNCONFIRMED" not in (work / ACME_ID / "README.md").read_text()
    assert "UNCONFIRMED" not in result.stdout


def files_containing(root: Path, needle: str) -> list[str]:
    hits = []
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            if needle in path.read_bytes().decode("utf-8", "replace"):
                hits.append(path.relative_to(root).as_posix())
    return sorted(hits)


def entry_names_below(root: Path) -> list[str]:
    return [p.name for p in root.rglob("*")]


def test_code_name_with_client(work, git_env):
    result = run_cairn(
        "init", "--engagement", PRICING, "--client", GLOBEX_CORP, "--code-name", FALCON,
        "--lead", LEAD, cwd=work, env=git_env,
    )
    assert result.returncode == 0, result.stderr
    eng = work / "falcon-pricing-study"
    meta = front_matter(eng / "engagement.md")
    assert meta["id"] == "falcon-pricing-study"
    assert meta["client"] == GLOBEX_CORP
    assert meta["client_code_name"] == FALCON
    assert files_containing(eng, "Globex") == ["engagement.md"]
    log = subprocess.run(["git", "log", "--format=%B"], cwd=eng, env=git_env,
                         capture_output=True, text=True, check=True).stdout
    assert "Globex" not in log
    assert "Globex" not in result.stdout
    assert not any("globex" in name.lower() for name in entry_names_below(work))


def test_code_name_without_client(work, git_env):
    result = run_cairn(
        "init", "--engagement", PRICING, "--code-name", FALCON, "--lead", LEAD,
        cwd=work, env=git_env,
    )
    assert result.returncode == 0, result.stderr
    eng = work / "falcon-pricing-study"
    assert front_matter(eng / "engagement.md")["client"] == ""
    assert files_containing(eng, "Globex") == []


def test_neither_client_nor_code_name(work, git_env):
    result = run_cairn("init", "--engagement", PRICING, "--lead", LEAD, cwd=work, env=git_env)
    assert result.returncode == 2
    assert "--client or --code-name" in result.stderr


def test_rollback_on_write_failure(work, monkeypatch):
    sibling = work / "sibling.txt"
    sibling.write_text("keep me")
    real_write = Transaction.write_bytes
    calls = {"n": 0}

    def failing_write(self, path, data):
        calls["n"] += 1
        if calls["n"] > 5:
            raise OSError("disk full (injected)")
        return real_write(self, path, data)

    monkeypatch.setattr(Transaction, "write_bytes", failing_write)
    opts = init_cmd.InitOptions(
        path=str(work / ACME_ID), engagement=FULFILLMENT, client=ACME, lead=LEAD, no_git=True
    )
    with pytest.raises(CairnError, match="initialization failed: disk full"):
        init_cmd.run(opts)
    assert not (work / ACME_ID).exists()
    assert sibling.read_text() == "keep me"
    assert sorted(p.name for p in work.iterdir()) == ["sibling.txt"]


def test_rollback_on_git_failure(work, monkeypatch, git_env):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", git_env["GIT_CONFIG_GLOBAL"])

    def failing_commit(path, message):
        subprocess.run(["git", "init", "--quiet"], cwd=path, check=True)
        raise CairnError("git commit failed: injected")

    monkeypatch.setattr("cairn.gitutil.init_and_commit", failing_commit)
    opts = init_cmd.InitOptions(
        path=str(work / ACME_ID), engagement=FULFILLMENT, client=ACME, lead=LEAD
    )
    with pytest.raises(CairnError, match="removed everything this run created"):
        init_cmd.run(opts)
    assert list(work.iterdir()) == []


def test_ctrl_c_at_first_prompt(work, monkeypatch):
    monkeypatch.chdir(work)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    def interrupt(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", interrupt)
    assert cli.main(["init", "--no-git"]) == 130
    assert list(work.iterdir()) == []
