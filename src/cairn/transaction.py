"""Record every path a run creates so a failure removes exactly those paths (R13, FR-017)."""

from __future__ import annotations

import shutil
from pathlib import Path


class Transaction:
    """Create folders and files, remembering each one; `rollback()` undoes only those.

    Used as a context manager: any exception (including KeyboardInterrupt) inside the
    block rolls back and re-raises.
    """

    def __init__(self) -> None:
        self._folders: list[Path] = []
        self._files: list[Path] = []
        self._git_dirs: list[Path] = []

    def mkdir(self, path: Path) -> bool:
        """Create one folder if it is missing. Returns True if this call created it."""
        path = Path(path)
        if path.is_dir():
            return False
        path.mkdir(parents=False)
        self._folders.append(path)
        return True

    def write_bytes(self, path: Path, data: bytes) -> None:
        """Write a new file. Never overwrites: an existing path raises FileExistsError."""
        path = Path(path)
        with open(path, "xb") as fh:
            self._files.append(path)
            fh.write(data)

    def mark_git_created(self, path: Path) -> None:
        """Record a `.git/` folder this run is about to create."""
        self._git_dirs.append(Path(path))

    def rollback(self) -> None:
        for path in reversed(self._files):
            path.unlink(missing_ok=True)
        for path in reversed(self._git_dirs):
            shutil.rmtree(path, ignore_errors=True)
        for path in reversed(self._folders):
            try:
                path.rmdir()
            except OSError:
                pass  # missing, or holds something this run did not create
        self._files.clear()
        self._folders.clear()
        self._git_dirs.clear()

    def __enter__(self) -> Transaction:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.rollback()
        return False
