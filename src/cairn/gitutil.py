"""Local git operations for a new engagement (R14). Never adds a remote or touches the network."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from cairn.report import CairnError

_IDENTITY_HINT = (
    'set it with git config --global user.name "Your Name" and '
    'git config --global user.email "you@example.com", or use --no-git'
)


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=False, capture_output=True, text=True)


def _nearest_existing(path: Path) -> Path:
    path = Path(path)
    while not path.exists():
        path = path.parent
    return path if path.is_dir() else path.parent


def preflight(path: Path | None = None) -> None:
    """Refuse early if git is missing or has no identity to commit with."""
    if shutil.which("git") is None:
        raise CairnError("git is not installed or not on PATH", hint="install git, or use --no-git")
    cwd = _nearest_existing(path or Path.cwd())
    for key in ("user.name", "user.email"):
        if not _git(["config", key], cwd).stdout.strip():
            raise CairnError(f"git {key} is not set", hint=_IDENTITY_HINT)


def inside_work_tree(path: Path) -> bool:
    result = _git(["rev-parse", "--is-inside-work-tree"], _nearest_existing(path))
    return result.returncode == 0 and result.stdout.strip() == "true"


def has_remote(path: Path) -> bool:
    return bool(_git(["remote"], _nearest_existing(path)).stdout.strip())


def init_and_commit(path: Path, message: str) -> str:
    """`git init`, add everything, make the initial commit. Returns the short SHA."""
    for args in (["init", "--quiet"], ["add", "-A"], ["commit", "--quiet", "-m", message]):
        result = _git(args, path)
        if result.returncode != 0:
            raise CairnError(f"git {args[0]} failed: {result.stderr.strip() or result.stdout.strip()}")
    return _git(["rev-parse", "--short", "HEAD"], path).stdout.strip()
