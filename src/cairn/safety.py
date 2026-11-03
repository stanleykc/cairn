"""Checks that run before `cairn init` writes anything (R11, R12, contracts/cli.md checks 2–6).

Every check only reads; a failed check raises CairnError and nothing has been written.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import cairn
from cairn import layout
from cairn.report import CairnError
from cairn.textutil import read_front_matter

MAX_LISTED = 10


def _is_framework_root(folder: Path) -> bool:
    pyproject = folder / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return data.get("project", {}).get("name") == "cairn"


def _package_project_root() -> Path | None:
    """The project root of the running package (an editable install), if there is one."""
    for folder in Path(cairn.__file__).resolve().parents:
        if _is_framework_root(folder):
            return folder
    return None


def _is_engagement(folder: Path) -> bool:
    if (folder / layout.MANIFEST_PATH).is_file():
        return True
    record = folder / "engagement.md"
    if not record.is_file():
        return False
    try:
        return read_front_matter(record.read_text(encoding="utf-8")).get("type") == "engagement"
    except (OSError, UnicodeDecodeError):
        return False


def check_not_in_framework(target: Path) -> None:
    target = Path(target).resolve()
    own_root = _package_project_root()
    for folder in (target, *target.parents):
        if _is_framework_root(folder) or folder == own_root:
            raise CairnError(
                "target is inside the Cairn framework repository",
                hint="create engagements outside the framework checkout, e.g. ~/engagements/<name>",
            )


def check_not_nested(target: Path, merge: bool) -> None:
    target = Path(target).resolve()
    for ancestor in target.parents:
        if _is_engagement(ancestor):
            raise CairnError(
                f"target is inside another engagement: {ancestor}",
                hint="engagements cannot be nested; choose a location outside it",
            )
    # Without --merge, an existing engagement is refused as a non-empty target instead.
    if merge and _is_engagement(target):
        raise CairnError(
            f"target is already an engagement: {target}",
            hint="use cairn refresh to update its framework files",
        )


def check_target_empty(target: Path, merge: bool, engagement_id: str) -> None:
    target = Path(target)
    if merge or not target.exists():
        return
    if not target.is_dir():
        raise CairnError(f"target exists and is not a folder: {target}")
    entries = sorted(p.name for p in target.iterdir())
    if not entries:
        return
    listed = "\n".join(f"  {name}" for name in entries[:MAX_LISTED])
    more = f"\n  … and {len(entries) - MAX_LISTED} more" if len(entries) > MAX_LISTED else ""
    raise CairnError(
        f"target folder is not empty: {target}\n{listed}{more}",
        hint=f"choose a distinct name such as {engagement_id}-2, or use --merge to add only missing items",
    )


def check_writable(target: Path) -> None:
    folder = Path(target)
    while not folder.exists():
        folder = folder.parent
    if not os.access(folder, os.W_OK | os.X_OK):
        raise CairnError(f"not writable: {folder}", hint="choose a location you can write to")


def check_assets(root: Path) -> None:
    missing = layout.missing_assets(root)
    if missing:
        raise CairnError(
            "framework assets are incomplete; missing:\n" + "\n".join(f"  {m}" for m in missing),
            hint=f"reinstall or update the Cairn framework (assets folder: {root})",
        )


def run_init_checks(target: Path, engagement_id: str, merge: bool) -> None:
    check_not_in_framework(target)
    check_not_nested(target, merge)
    check_target_empty(target, merge, engagement_id)
    check_writable(target)
    check_assets(layout.assets_root())
