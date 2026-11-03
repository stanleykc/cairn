import subprocess

from conftest import ACME_ID, INIT_ACME, run_cairn


def git(*args, cwd, env):
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True
    ).stdout


def test_default_run_commits_once(tmp_path, git_env):
    result = run_cairn(*INIT_ACME, cwd=tmp_path, env=git_env)
    assert result.returncode == 0, result.stderr
    eng = tmp_path / ACME_ID
    log = git("log", "--format=%s", cwd=eng, env=git_env).splitlines()
    assert log == [f"Initialize engagement {ACME_ID} (cairn 0.1.0)"]
    assert git("remote", cwd=eng, env=git_env) == ""
    assert git("status", "--porcelain", cwd=eng, env=git_env) == ""
    tracked = git("ls-files", cwd=eng, env=git_env).splitlines()
    assert "10-sources/raw/.gitkeep" in tracked
    assert "git: initialized, initial commit" in result.stdout
    assert "(no remote)" in result.stdout


def test_no_git(tmp_path, git_env):
    result = run_cairn(*INIT_ACME, "--no-git", cwd=tmp_path, env=git_env)
    assert result.returncode == 0
    assert not (tmp_path / ACME_ID / ".git").exists()
    assert "git: skipped (--no-git)" in result.stdout


def make_parent_repo(tmp_path, env):
    parent = tmp_path / "parent"
    parent.mkdir()
    git("init", "--quiet", cwd=parent, env=env)
    (parent / "notes.txt").write_text("x")
    git("add", "-A", cwd=parent, env=env)
    git("commit", "--quiet", "-m", "parent", cwd=parent, env=env)
    return parent


def test_inside_existing_repo(tmp_path, git_env):
    parent = make_parent_repo(tmp_path, git_env)
    result = run_cairn(*INIT_ACME, cwd=parent, env=git_env)
    assert result.returncode == 0, result.stderr
    assert not (parent / ACME_ID / ".git").exists()
    assert git("log", "--format=%s", cwd=parent, env=git_env).splitlines() == ["parent"]
    assert "uncommitted" in result.stdout
    assert "has a remote" not in result.stdout


def test_inside_existing_repo_with_remote_warns(tmp_path, git_env):
    parent = make_parent_repo(tmp_path, git_env)
    git("remote", "add", "origin", "https://example.invalid/x.git", cwd=parent, env=git_env)
    result = run_cairn(*INIT_ACME, cwd=parent, env=git_env)
    assert result.returncode == 0, result.stderr
    assert "has a remote" in result.stdout
    assert git("log", "--format=%s", cwd=parent, env=git_env).splitlines() == ["parent"]


def test_missing_identity(tmp_path, git_env):
    home = tmp_path / "home"
    home.mkdir()
    empty = tmp_path / "empty-gitconfig"
    empty.write_text("")
    env = git_env | {"GIT_CONFIG_GLOBAL": str(empty), "HOME": str(home)}
    for key in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                "GIT_COMMITTER_EMAIL", "EMAIL"):
        env.pop(key, None)
    work = tmp_path / "work"
    work.mkdir()
    result = run_cairn(*INIT_ACME, cwd=work, env=env)
    assert result.returncode == 1
    assert "git config" in result.stderr
    assert "--no-git" in result.stderr
    assert list(work.iterdir()) == []
