"""`charter.py status` and `check` finish in under 1 s on about 2,000 markdown files (plan)."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import PACKAGE_ASSETS

SCRIPT = PACKAGE_ASSETS / "skills" / "charter" / "scripts" / "charter.py"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "charter"
FOLDERS = ("30-observations", "40-synthesis/findings", "40-synthesis/issues", "50-options", "_inbox")


@pytest.mark.skipif(os.environ.get("CAIRN_SLOW_MACHINE") == "1",
                    reason="CAIRN_SLOW_MACHINE=1: timing goals are not meaningful on this machine")
def test_status_and_check_under_one_second(tmp_path):
    root = tmp_path / "eng"
    shutil.copytree(FIXTURES / "approved", root)
    for n in range(2000):
        folder = root / FOLDERS[n % len(FOLDERS)]
        folder.mkdir(parents=True, exist_ok=True)
        q, h = f"Q-{n % 4 + 1:03d}", f"H-{n % 3 + 1:03d}"
        (folder / f"O-{n + 100:04d}.md").write_text(
            f'---\nid: "O-{n + 100:04d}"\ntype: observation\nstatus: proposed\n'
            f'source: "S-{n % 50 + 1:03d}"\nquestions: ["{q}"]\nsupports: ["{h}"]\n---\n\n'
            f"Synthetic observation {n} about {q}.\n" + "Padding text for a realistic size.\n" * 20
        )
    for command in ("status", "check"):
        start = time.monotonic()
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), command],
                                capture_output=True, text=True)
        elapsed = time.monotonic() - start
        assert result.returncode == 0, result.stderr
        assert elapsed < 1.0, f"{command} took {elapsed:.2f}s"
