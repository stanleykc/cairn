"""Shared errors and the run report printed as the command summary (data-model §7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class CairnError(Exception):
    """A refusal or failure. Printed as `cairn: error: <message>` plus an optional hint."""

    exit_code = 1

    def __init__(self, message: str, hint: str | None = None, exit_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint
        if exit_code is not None:
            self.exit_code = exit_code


class UsageError(CairnError):
    """A bad or missing argument. Nothing was written."""

    exit_code = 2


@dataclass
class Report:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    kept_edited: list[str] = field(default_factory=list)
    backed_up: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    engagement_id: str = ""
    engagement_path: Path | None = None
    framework_version: str = ""
    previous_version: str = ""
    git_status: str = ""
    counts: dict[str, int] = field(default_factory=dict)
