"""`cairn init`: resolve inputs → safety checks → write in one transaction → git."""

from __future__ import annotations

import json
import string
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from cairn import gitutil, layout, safety
from cairn.report import CairnError, Report, UsageError
from cairn.transaction import Transaction
from cairn.textutil import slugify, yaml_str

MODEL_USE_VALUES = ("allowed", "restricted", "unconfirmed")

MODEL_USE_WARNING = (
    "Model-use policy is UNCONFIRMED. Set model_use in engagement.md before ingesting any source."
)

README_MODEL_USE_WARNING = """
> **Warning: the client's model-use policy is UNCONFIRMED.**
> Set `model_use` in `engagement.md` (and `00-charter/scope.md`) before any source is
> ingested. Until it is set, treat every source as "ask before sending it to an external
> AI service".
"""

NEXT_STEPS = (
    "Confirm the client's model-use policy (engagement.md, 00-charter/scope.md)",
    "Run the `charter` skill from inside the engagement folder",
    "Put original files in 10-sources/raw/",
)

RAW_FOLDER = "10-sources/raw"


@dataclass
class InitOptions:
    engagement: str
    lead: str
    path: str | None = None
    client: str = ""
    code_name: str = ""
    team: list[str] = field(default_factory=list)
    start_date: date = field(default_factory=date.today)
    model_use: str = "unconfirmed"
    merge: bool = False
    no_git: bool = False


def resolve_target(opts: InitOptions, cwd: Path | None = None) -> tuple[Path, str]:
    """The engagement folder and its `id` (R15)."""
    if opts.path:
        target = Path(opts.path).expanduser().resolve()
        engagement_id = slugify(target.name)
        if not engagement_id:
            raise UsageError(f"folder name gives an empty engagement id: {opts.path!r}")
        return target, engagement_id
    who = slugify(opts.code_name or opts.client)
    what = slugify(opts.engagement)
    if not who or not what:
        raise UsageError(
            "client (or code name) and engagement name must contain letters or digits",
            hint="or give the folder explicitly: cairn init <path> ...",
        )
    engagement_id = f"{who}-{what}"
    return (cwd or Path.cwd()).resolve() / engagement_id, engagement_id


def render_seed(rel: str, values: dict[str, str]) -> bytes:
    text = (layout.assets_root() / "seed" / rel).read_text(encoding="utf-8")
    return string.Template(text).substitute(values).encode("utf-8")


def _skills_list(skills: list[tuple[str, str]]) -> str:
    if not skills:
        return "None installed yet."
    return "\n".join(f"- `{name}` — {desc}" if desc else f"- `{name}`" for name, desc in skills)


def _seed_values(opts: InitOptions, engagement_id: str, version: str, skills) -> dict[str, str]:
    client_display = opts.code_name or opts.client
    return {
        "id": engagement_id,
        "engagement_name": opts.engagement,
        "client_display": client_display,
        "lead_consultant": opts.lead,
        "start_date": opts.start_date.isoformat(),
        "created": date.today().isoformat(),
        "framework_version": version,
        "model_use": opts.model_use,
        "id_q": yaml_str(engagement_id),
        "engagement_name_q": yaml_str(opts.engagement),
        "client_q": yaml_str(opts.client),  # only engagement.md uses this (FR-016)
        "client_code_name_q": yaml_str(opts.code_name),
        "lead_consultant_q": yaml_str(opts.lead),
        "framework_version_q": yaml_str(version),
        "team_json": json.dumps(opts.team, ensure_ascii=False),
        "model_use_warning": README_MODEL_USE_WARNING if opts.model_use == "unconfirmed" else "",
        "skills_list": _skills_list(skills),
    }


def _validate(opts: InitOptions) -> None:
    opts.engagement = opts.engagement.strip()
    opts.client = opts.client.strip()
    opts.code_name = opts.code_name.strip()
    opts.lead = opts.lead.strip()
    opts.team = [t.strip() for t in opts.team if t.strip()]
    if not opts.engagement:
        raise UsageError("an engagement name is required (--engagement)")
    if not opts.client and not opts.code_name:
        raise UsageError("a client name or code name is required (--client or --code-name)")
    if not opts.lead:
        raise UsageError("a lead consultant is required (--lead)")
    if opts.model_use not in MODEL_USE_VALUES:
        raise UsageError(
            f"invalid model-use policy: {opts.model_use!r}",
            hint="choose one of: " + ", ".join(MODEL_USE_VALUES),
        )


def run(opts: InitOptions) -> Report:
    _validate(opts)
    target, engagement_id = resolve_target(opts)
    safety.run_init_checks(target, engagement_id, opts.merge)
    in_work_tree = False
    if not opts.no_git:
        gitutil.preflight(target)
        in_work_tree = gitutil.inside_work_tree(target)

    root = layout.assets_root()
    version = layout.framework_version()
    framework = layout.framework_files(root)
    skills = layout.bundled_skills(root)
    values = _seed_values(opts, engagement_id, version, skills)

    report = Report(engagement_id=engagement_id, engagement_path=target, framework_version=version)
    try:
        with Transaction() as tx:
            _write(tx, target, values, framework, report)
            _git(tx, target, engagement_id, version, opts, in_work_tree, report)
    except CairnError as exc:
        raise CairnError(
            f"initialization failed: {exc.message}; removed everything this run created",
            hint=exc.hint,
        ) from exc
    except Exception as exc:
        raise CairnError(
            f"initialization failed: {exc}; removed everything this run created"
        ) from exc

    report.counts["skills"] = sum(
        1 for name, _ in skills if f"{layout.SKILLS_DIR}/{name}/SKILL.md" in report.created
    )
    if opts.model_use == "unconfirmed":
        report.warnings.insert(0, MODEL_USE_WARNING)
    report.next_steps = list(NEXT_STEPS)
    return report


def _make_parents(tx: Transaction, path: Path, stop: Path) -> None:
    """Create the missing folders between `stop` and `path`, top-down."""
    missing = []
    folder = path
    while folder != stop and not folder.exists():
        missing.append(folder)
        folder = folder.parent
    for folder in reversed(missing):
        tx.mkdir(folder)


def _write(tx: Transaction, target: Path, values, framework: dict[str, bytes], report: Report) -> None:
    raw_existed = (target / RAW_FOLDER).exists()

    # (3a) the target and any missing ancestors, so `cairn init a/b/eng` works
    _make_parents(tx, target, Path(target.anchor))

    # (3b) canonical folders
    created_folders = []
    for rel in layout.CANONICAL_FOLDERS:
        if tx.mkdir(target / rel):
            created_folders.append(rel)
            report.created.append(rel + "/")
        else:
            report.skipped.append(rel + "/")
    if raw_existed:
        # Originals are never touched (FR-014); list them so the consultant sees they were left alone.
        for path in sorted((target / RAW_FOLDER).rglob("*")):
            if path.is_file():
                report.skipped.append(path.relative_to(target).as_posix())

    # (3c) seed files
    seeds_written = 0
    for rel in layout.SEED_FILES:
        dest = target / rel
        if dest.exists():
            report.skipped.append(rel)
            continue
        tx.write_bytes(dest, render_seed(rel, values))
        report.created.append(rel)
        seeds_written += 1

    # (3d) framework files: templates and skills (copied, never symlinked)
    written: dict[str, bytes] = {}
    for rel, data in framework.items():
        dest = target / rel
        if dest.exists():
            report.skipped.append(rel)  # left out of the manifest, so refresh treats it as edited
            continue
        _make_parents(tx, dest.parent, target)
        tx.write_bytes(dest, data)
        report.created.append(rel)
        written[rel] = data

    # (3e) manifest of the framework files this run wrote
    manifest_path = target / layout.MANIFEST_PATH
    _make_parents(tx, manifest_path.parent, target)
    manifest = layout.build_manifest(written, values["framework_version"])
    tx.write_bytes(manifest_path, layout.manifest_bytes(manifest))

    # (3f) keep empty canonical folders in version control
    for rel in created_folders:
        folder = target / rel
        if not any(folder.iterdir()):
            tx.write_bytes(folder / ".gitkeep", b"")

    report.counts.update(
        folders=len(created_folders),
        seed_files=seeds_written,
        templates=sum(1 for rel in written if rel.startswith("_templates/")),
    )


def _git(tx, target, engagement_id, version, opts, in_work_tree, report: Report) -> None:
    if opts.no_git:
        report.git_status = "skipped (--no-git)"
        return
    if in_work_tree:
        report.git_status = (
            "not initialized: the target is inside an existing git repository; "
            "the new files are uncommitted"
        )
        if gitutil.has_remote(target):
            report.warnings.append(
                "The enclosing git repository has a remote. Pushing it would send client "
                "material off this machine."
            )
        return
    tx.mark_git_created(target / ".git")
    message = f"Initialize engagement {engagement_id} (cairn {version})"
    sha = gitutil.init_and_commit(target, message)
    report.git_status = f"initialized, initial commit {sha} (no remote)"
