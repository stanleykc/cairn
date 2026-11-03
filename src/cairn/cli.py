"""Command line for `cairn init` and `cairn refresh` (contracts/cli.md)."""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
import textwrap
from datetime import date

from cairn import init_cmd, layout, refresh_cmd
from cairn.report import CairnError, Report, UsageError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cairn", description="Create and refresh Cairn engagement folders."
    )
    parser.add_argument(
        "--version", action="version", version=f"cairn {layout.framework_version()}"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    init = sub.add_parser("init", help="create a new engagement folder")
    init.add_argument("path", nargs="?", metavar="PATH",
                      help="engagement folder (default: ./<client-or-code>-<engagement>)")
    init.add_argument("--engagement", metavar="NAME", help="engagement name, as typed")
    init.add_argument("--client", metavar="NAME",
                      help="real client name (optional with --code-name; kept only in engagement.md)")
    init.add_argument("--code-name", metavar="CODE",
                      help="client code name used for the folder, id, README and commit message")
    init.add_argument("--lead", metavar="NAME",
                      help="lead consultant (default: git config user.name, then $USER)")
    init.add_argument("--team", metavar="NAME", action="append", default=[],
                      help="team member (repeatable)")
    init.add_argument("--start-date", metavar="YYYY-MM-DD", help="start date (default: today)")
    init.add_argument("--model-use", choices=init_cmd.MODEL_USE_VALUES, default=None,
                      help="client's model-use policy (default: unconfirmed)")
    init.add_argument("--merge", action="store_true",
                      help="allow a non-empty existing folder; add only missing items")
    init.add_argument("--no-git", action="store_true", help="skip version control")
    init.set_defaults(handler=_init)

    refresh = sub.add_parser("refresh", help="update framework files in an existing engagement")
    refresh.add_argument("path", nargs="?", default=".", metavar="PATH",
                         help="engagement root (default: .)")
    refresh.add_argument("--replace-edited", action="store_true",
                         help="without a terminal, replace edited framework files after backing them up")
    refresh.set_defaults(handler=_refresh)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not getattr(args, "handler", None):
        parser.print_help(sys.stderr)
        return 2
    try:
        return args.handler(args)
    except CairnError as exc:
        print(f"cairn: error: {exc.message}", file=sys.stderr)
        if exc.hint:
            print(f"hint: {exc.hint}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        print("\ncairn: interrupted", file=sys.stderr)
        return 130


# --- init -------------------------------------------------------------------


def _default_lead() -> str:
    try:
        name = subprocess.run(
            ["git", "config", "user.name"], check=False, capture_output=True, text=True
        ).stdout.strip()
    except OSError:
        name = ""
    if name:
        return name
    try:
        return os.environ.get("USER") or getpass.getuser()
    except (KeyError, OSError):
        return ""


def _ask(prompt: str, default: str = "", required: bool = False) -> str:
    shown = f"{prompt} [{default}]: " if default else f"{prompt}: "
    while True:
        try:
            answer = input(shown).strip()
        except EOFError:
            raise UsageError(f"no answer for: {prompt}") from None
        answer = answer or default
        if answer or not required:
            return answer
        print("  A value is required.", file=sys.stderr)


def _init(args) -> int:
    interactive = sys.stdin.isatty()
    engagement = args.engagement
    code_name = args.code_name
    client = args.client
    lead = args.lead
    model_use = args.model_use

    try:
        start_date = date.fromisoformat(args.start_date) if args.start_date else date.today()
    except ValueError:
        raise UsageError(f"--start-date must be YYYY-MM-DD, got {args.start_date!r}") from None

    if interactive:
        # All prompts come before anything is written (contracts/cli.md).
        if not engagement:
            engagement = _ask("Engagement name", required=True)
        if not client and not code_name:
            code_name = _ask("Client code name (optional, blank = none)")
            if code_name:
                client = _ask("Client name (optional, blank = leave it out)")
            else:
                client = _ask("Client name", required=True)
        if not lead:
            lead = _ask("Lead consultant", default=_default_lead(), required=True)
        if model_use is None:
            while True:
                model_use = _ask("Model-use policy (allowed, restricted, unconfirmed)",
                                 default="unconfirmed")
                if model_use in init_cmd.MODEL_USE_VALUES:
                    break
                print("  Choose allowed, restricted or unconfirmed.", file=sys.stderr)
    else:
        missing = []
        if not engagement:
            missing.append("--engagement")
        if not client and not code_name:
            missing.append("--client or --code-name")
        lead = lead or _default_lead()
        if not lead:
            missing.append("--lead")
        if missing:
            raise UsageError(
                "missing required option(s): " + ", ".join(missing),
                hint="pass them as options, or run in a terminal to be prompted",
            )

    opts = init_cmd.InitOptions(
        path=args.path,
        engagement=engagement or "",
        client=client or "",
        code_name=code_name or "",
        lead=lead or "",
        team=args.team,
        start_date=start_date,
        model_use=model_use or "unconfirmed",
        merge=args.merge,
        no_git=args.no_git,
    )
    report = init_cmd.run(opts)
    _print_init(report)
    return 0


def _print_init(report: Report) -> None:
    c = report.counts
    print(f"Created engagement {report.engagement_id} at {report.engagement_path}")
    print(
        f"  framework {report.framework_version} · {c.get('folders', 0)} folders · "
        f"{c.get('seed_files', 0)} seed files · {c.get('templates', 0)} templates · "
        f"{c.get('skills', 0)} skills"
    )
    print(f"  git: {report.git_status}")
    for warning in report.warnings:
        print()
        print(textwrap.fill(warning, width=88, initial_indent="! ", subsequent_indent="  "))
    if report.skipped:
        print()
        print("Skipped (already present):")
        for rel in report.skipped:
            print(f"  {rel}")
    print()
    print("Next steps:")
    for n, step in enumerate(report.next_steps, 1):
        print(f"  {n}. {step}")


# --- refresh ----------------------------------------------------------------


def _confirm(rel: str) -> bool:
    try:
        answer = input(
            f"{rel} was edited in this engagement. Replace it (your version is backed up)? [y/N] "
        )
    except EOFError:
        return False
    return answer.strip().lower() in ("y", "yes")


def _refresh(args) -> int:
    confirm = _confirm if sys.stdin.isatty() else None
    report = refresh_cmd.run(args.path, replace_edited=args.replace_edited, confirm=confirm)
    _print_refresh(report)
    return 0


def _print_refresh(report: Report) -> None:
    print(
        f"Refreshed {report.engagement_id}: framework "
        f"{report.previous_version} → {report.framework_version}"
    )
    rows = (
        ("updated:", report.updated),
        ("added:  ", report.added),
        ("removed:", report.removed),
        ("kept (edited, not replaced):", report.kept_edited),
        ("backed up:", report.backed_up),
    )
    any_rows = False
    for label, paths in rows:
        if paths:
            any_rows = True
            print(f"  {label} {', '.join(paths)}")
    if not any_rows and report.previous_version == report.framework_version:
        print("  nothing to change")
        print("Content folders untouched.")
        return
    print(
        "Content folders untouched. Suggested: "
        f'git add -A && git commit -m "Refresh Cairn to {report.framework_version}"'
    )
