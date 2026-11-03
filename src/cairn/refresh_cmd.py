"""`cairn refresh`: bring templates and Cairn skills up to the running framework version (R17).

Writes only under `_templates/`, the manifest-listed or bundled `.claude/skills/<name>/`
folders and `.cairn/`, plus the single `framework_version:` line of `engagement.md`.
All-or-nothing: on failure every changed file is restored from memory.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from cairn import layout, safety
from cairn.report import CairnError, Report
from cairn.textutil import read_front_matter, sha256_bytes

_VERSION_LINE = re.compile(r'^framework_version:[ \t]*(?:"[^"\n]*"|\'[^\'\n]*\'|[^\s#]*)', re.M)
_FRAMEWORK_AREAS = ("_templates/", layout.SKILLS_DIR + "/")


def _in_framework_area(rel: str) -> bool:
    return rel.startswith(_FRAMEWORK_AREAS) and ".." not in Path(rel).parts


def _check(root: Path) -> tuple[dict, dict, str]:
    record = root / "engagement.md"
    meta = {}
    if record.is_file():
        meta = read_front_matter(record.read_text(encoding="utf-8"))
    if meta.get("type") != "engagement":
        raise CairnError(
            f"not a Cairn engagement: {root}",
            hint="run cairn refresh inside an engagement folder, or pass its path",
        )
    manifest = layout.read_manifest(root)
    old = meta.get("framework_version", "")
    new = layout.framework_version()
    if layout.parse_version(old) > layout.parse_version(new):
        raise CairnError(
            f"engagement uses framework {old}, newer than the running framework {new}",
            hint="update the Cairn framework, then refresh again",
        )
    safety.check_assets(layout.assets_root())
    return meta, manifest, new


def _classify(root: Path, manifest_files: dict[str, str], framework: dict[str, bytes]) -> dict[str, str]:
    """Map each framework path to an action, per contracts/framework-manifest.md."""
    plan = {}
    for rel in sorted(set(manifest_files) | set(framework)):
        if not _in_framework_area(rel):
            continue
        path = root / rel
        in_f = rel in framework
        if not path.is_file():
            plan[rel] = "add" if in_f else "drop"
            continue
        current = sha256_bytes(path.read_bytes())
        unchanged = rel in manifest_files and current == manifest_files[rel]
        if not in_f:
            plan[rel] = "remove" if unchanged else "keep-dropped"
        elif current == sha256_bytes(framework[rel]):
            plan[rel] = "keep" if unchanged else "keep-rehash"
        else:
            plan[rel] = "update" if unchanged else "edited"
    return plan


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(f".{path.name}.cairn-tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _backup_dir(root: Path) -> Path:
    base = root / ".cairn" / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    folder, n = base, 2
    while folder.exists():
        folder = base.with_name(f"{base.name}-{n}")
        n += 1
    return folder


def run(path, *, replace_edited: bool = False, confirm: Callable[[str], bool] | None = None) -> Report:
    root = Path(path).resolve()
    meta, manifest, new_version = _check(root)
    old_version = meta["framework_version"]
    framework = layout.framework_files(layout.assets_root())
    old_files: dict[str, str] = manifest["files"]
    plan = _classify(root, old_files, framework)

    # Every question is asked before anything is written.
    replace = {
        rel for rel, action in plan.items()
        if action == "edited" and (confirm(rel) if confirm else replace_edited)
    }

    report = Report(
        engagement_id=meta.get("id") or root.name,
        engagement_path=root,
        framework_version=new_version,
        previous_version=old_version,
    )
    record_path = root / "engagement.md"
    manifest_path = root / layout.MANIFEST_PATH
    record_orig = record_path.read_bytes()
    manifest_orig = manifest_path.read_bytes()
    originals = {
        rel: (root / rel).read_bytes()
        for rel, action in plan.items()
        if action in ("update", "remove") or rel in replace
    }

    # The manifest keeps the old hash of an edited file that was kept, so it stays "edited".
    new_files = {}
    for rel, action in plan.items():
        if action in ("keep", "keep-rehash", "update", "add") or rel in replace:
            new_files[rel] = sha256_bytes(framework[rel])
        elif action == "edited" and rel in old_files:
            new_files[rel] = old_files[rel]

    record_text = record_orig.decode("utf-8")
    new_record = _set_version(record_text, new_version).encode("utf-8")
    files_changed = new_files != old_files
    new_manifest = None
    if files_changed or manifest.get("framework_version") != new_version:
        new_manifest = {
            "schema": 1,
            "framework_version": new_version,
            "written": datetime.now().isoformat(timespec="seconds"),
            "files": dict(sorted(new_files.items())),
        }

    changed: list[str] = []
    added: list[str] = []
    created_dirs: list[Path] = []
    wrote_manifest = wrote_record = False
    try:
        if replace:
            backups = _backup_dir(root)
            for rel in sorted(replace):
                dest = backups / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(originals[rel])
                report.backed_up.append(dest.relative_to(root).as_posix())
        for rel, action in plan.items():
            target = root / rel
            if action == "update" or rel in replace:
                changed.append(rel)
                _atomic_write(target, framework[rel])
                report.updated.append(rel)
            elif action == "add":
                created_dirs += _mkdirs(target.parent)
                added.append(rel)
                _atomic_write(target, framework[rel])
                report.added.append(rel)
            elif action == "remove":
                changed.append(rel)
                target.unlink()
                _prune_skill_folder(root, target.parent)
                report.removed.append(rel)
            elif action in ("edited", "keep-dropped"):
                report.kept_edited.append(rel)
        if new_manifest is not None:
            wrote_manifest = True
            _atomic_write(manifest_path, layout.manifest_bytes(new_manifest))
        if new_record != record_orig:
            wrote_record = True
            _atomic_write(record_path, new_record)
    except BaseException as exc:
        _restore(root, changed, added, created_dirs, originals)
        if wrote_manifest:
            manifest_path.write_bytes(manifest_orig)
        if wrote_record:
            record_path.write_bytes(record_orig)
        if isinstance(exc, Exception):
            raise CairnError(f"refresh failed: {exc}; restored original files") from exc
        raise
    return report


def _set_version(text: str, version: str) -> str:
    """Replace only the `framework_version:` value in the front matter, keeping any comment."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise CairnError("engagement.md has no front matter")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise CairnError("engagement.md front matter is not closed") from None
    front = "\n".join(lines[1:end])
    new_front, count = _VERSION_LINE.subn(f'framework_version: "{version}"', front, count=1)
    if count != 1:
        raise CairnError("engagement.md has no framework_version line")
    return "\n".join([lines[0], new_front, *lines[end:]])


def _mkdirs(folder: Path) -> list[Path]:
    """Create `folder` and missing parents; return the folders created, top-down."""
    missing = []
    while not folder.exists():
        missing.append(folder)
        folder = folder.parent
    for f in reversed(missing):
        f.mkdir()
    return list(reversed(missing))


def _prune_skill_folder(root: Path, folder: Path) -> None:
    """Remove empty folders left behind inside a skill, up to (not including) `.claude/skills`."""
    stop = root / layout.SKILLS_DIR
    while folder != stop and stop in folder.parents and not any(folder.iterdir()):
        folder.rmdir()
        folder = folder.parent


def _restore(root: Path, changed, added, created_dirs, originals) -> None:
    for rel in added:
        (root / rel).unlink(missing_ok=True)
    for folder in reversed(created_dirs):
        try:
            folder.rmdir()
        except OSError:
            pass
    for rel in changed:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(originals[rel])
