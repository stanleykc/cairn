"""The canonical engagement layout, the framework assets, and the manifest (data-model §3–§6).

Test-only hooks (R19). Integration tests run the CLI as a subprocess against a temporary
copy of the assets at another version. Two environment variables make that possible, and
nothing else in the package reads them:

- `CAIRN_ASSETS_DIR` replaces the package `assets/` folder.
- `CAIRN_FRAMEWORK_VERSION` replaces `cairn.__version__`.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from importlib.resources import files
from pathlib import Path

import cairn
from cairn.report import CairnError
from cairn.textutil import read_front_matter, sha256_bytes

CANONICAL_FOLDERS = (
    "_inbox",
    "_templates",
    "00-charter",
    "10-sources",
    "10-sources/raw",
    "10-sources/extracted",
    "20-research",
    "30-observations",
    "40-synthesis",
    "40-synthesis/findings",
    "40-synthesis/issues",
    "40-synthesis/opportunities",
    "50-options",
    "60-log",
    "70-views",
    "80-deliverables",
)

SEED_FILES = (
    "README.md",
    "engagement.md",
    "00-charter/scope.md",
    "00-charter/questions.md",
    "00-charter/hypotheses.md",
    "00-charter/assumptions.md",
    "00-charter/stakeholders.md",
    "00-charter/lenses.md",
    "10-sources/index.md",
    "60-log/decisions.md",
    "60-log/lessons.md",
    "60-log/changelog.md",
)

# (type, ID prefix, file name in assets/templates/ and _templates/)
TEMPLATES = (
    ("source", "S", "source.md"),
    ("observation", "O", "observation.md"),
    ("question", "Q", "question.md"),
    ("hypothesis", "H", "hypothesis.md"),
    ("assumption", "A", "assumption.md"),
    ("research", "R", "research.md"),
    ("finding", "F", "finding.md"),
    ("issue", "I", "issue.md"),
    ("opportunity", "P", "opportunity.md"),
    ("option", "X", "option.md"),
    ("decision", "D", "decision.md"),
    ("lesson", "L", "lesson.md"),
)

MANIFEST_PATH = ".cairn/manifest.json"
SKILLS_DIR = ".claude/skills"

REAL_ID = re.compile(r"\b[SOQHARFIPXDL]-\d{3}\b")
# Files holding names the consultant typed, so an ID-like name is not an object (FR-007).
_TYPED_NAME_FILES = ("README.md", "engagement.md")


def assets_root() -> Path:
    override = os.environ.get("CAIRN_ASSETS_DIR")
    if override:
        return Path(override)
    return Path(str(files("cairn") / "assets"))


def framework_version() -> str:
    return os.environ.get("CAIRN_FRAMEWORK_VERSION") or cairn.__version__


def parse_version(s: str) -> tuple[int, ...]:
    """Compare versions as integer tuples; a pre-release or build suffix is ignored (R18)."""
    core = re.split(r"[-+]", s.strip(), maxsplit=1)[0]
    try:
        return tuple(int(part) for part in core.split("."))
    except ValueError:
        raise CairnError(f"not a valid framework version: {s!r}") from None


def _skill_dirs(root: Path) -> list[Path]:
    skills = root / "skills"
    if not skills.is_dir():
        return []
    return sorted(p for p in skills.iterdir() if p.is_dir() and not p.name.startswith("."))


def missing_assets(root: Path) -> list[str]:
    """Asset paths (relative to `root`) that must exist but don't."""
    missing = [f"seed/{rel}" for rel in SEED_FILES if not (root / "seed" / rel).is_file()]
    missing += [
        f"templates/{name}" for _, _, name in TEMPLATES if not (root / "templates" / name).is_file()
    ]
    missing += [
        f"skills/{d.name}/SKILL.md" for d in _skill_dirs(root) if not (d / "SKILL.md").is_file()
    ]
    return missing


def framework_files(root: Path) -> dict[str, bytes]:
    """Every framework-provided file, keyed by its path in the engagement (R10)."""
    result = {f"_templates/{name}": (root / "templates" / name).read_bytes() for _, _, name in TEMPLATES}
    for skill in _skill_dirs(root):
        for path in sorted(skill.rglob("*")):
            # Bytecode caches appear next to a skill's scripts once they are imported.
            if path.is_file() and "__pycache__" not in path.relative_to(skill).parts:
                rel = path.relative_to(skill).as_posix()
                result[f"{SKILLS_DIR}/{skill.name}/{rel}"] = path.read_bytes()
    return result


def bundled_skills(root: Path) -> list[tuple[str, str]]:
    """(name, description) for each bundled skill, from its SKILL.md front matter."""
    result = []
    for skill in _skill_dirs(root):
        meta = read_front_matter((skill / "SKILL.md").read_text(encoding="utf-8"))
        result.append((skill.name, meta.get("description", "")))
    return result


def build_manifest(files_: dict[str, bytes], version: str) -> dict:
    return {
        "schema": 1,
        "framework_version": version,
        "written": datetime.now().isoformat(timespec="seconds"),
        "files": {path: sha256_bytes(files_[path]) for path in sorted(files_)},
    }


def manifest_bytes(manifest: dict) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_manifest(engagement: Path) -> dict:
    path = Path(engagement) / MANIFEST_PATH
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CairnError(
            f"framework manifest is missing: {path}",
            hint="this engagement looks damaged; rebuilding the manifest is not supported yet",
        ) from None
    except (OSError, ValueError) as exc:
        raise CairnError(f"framework manifest could not be read: {path} ({exc})") from None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise CairnError(f"framework manifest is not valid: {path}")
    return manifest


def _content_walk(path: Path):
    """Yield (dirpath, dirnames, filenames) below `path`, skipping dot-folders (R9)."""
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        yield Path(dirpath), dirnames, filenames


def check_layout(path: Path, *, fresh: bool = True) -> list[str]:
    """Problems with the engagement at `path`; an empty list means the layout is correct (SC-002).

    `fresh=True` also requires that no numbered object exists yet (FR-007).
    """
    path = Path(path)
    problems: list[str] = []
    found = set()
    md_files: list[str] = []
    for dirpath, dirnames, filenames in _content_walk(path):
        for d in dirnames:
            found.add((dirpath / d).relative_to(path).as_posix())
        for f in filenames:
            if f.endswith(".md"):
                md_files.append((dirpath / f).relative_to(path).as_posix())
    expected = set(CANONICAL_FOLDERS)
    problems += [f"missing folder: {d}" for d in sorted(expected - found)]
    problems += [f"extra folder: {d}" for d in sorted(found - expected)]
    problems += [f"missing seed file: {f}" for f in SEED_FILES if not (path / f).is_file()]

    for rel in sorted(md_files):
        text = (path / rel).read_text(encoding="utf-8")
        # Entry-form templates have no front matter by design (R16); T015 validates templates.
        if rel != "README.md" and not rel.startswith("_templates/") and not read_front_matter(text):
            problems.append(f"no front matter: {rel}")
        if fresh and rel not in _TYPED_NAME_FILES and REAL_ID.search(text):
            problems.append(f"numbered object in a fresh engagement: {rel}")
    return problems
