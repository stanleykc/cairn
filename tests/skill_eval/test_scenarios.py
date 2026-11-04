"""Run each scripted scenario in `scenarios/*.yaml` against a live model (opt-in, R20).

Scenario keys:
- `name`: shown in the test id.
- `fixture`: `fresh`, or the name of a folder in `tests/fixtures/charter/`.
- `model_use` (optional): force the policy in both files before the run.
- `edits` (optional): `[path, old, new]` text replacements made before the first commit.
- `turns`: the consultant's messages; the first one usually starts with `/charter`.
- `expect`: per-scenario assertions (see `check_expectations`).

Every scenario also asserts: `charter.py check` exits 0; no tool call names a path under
`10-sources/`; the canary never appears in the transcript or in any changed file; and no
charter item is `client-ready`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
CANARY = "CANARY-7f3a"  # same as conftest.CANARY
SCENARIOS = sorted((HERE / "scenarios").glob("*.yaml"))
SCRIPT = ".claude/skills/charter/scripts/charter.py"
TURN_TIMEOUT = 900


class Transcript:
    def __init__(self):
        self.events: list = []
        self.session_id: str | None = None

    def add(self, stdout: str) -> None:
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            self.events.append(event)
            self.session_id = event.get("session_id") or self.session_id

    def tool_calls(self) -> list:
        calls = []
        for event in self.events:
            if event.get("type") != "assistant":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    calls.append(block)
        return calls

    def assistant_text(self) -> str:
        parts = []
        for event in self.events:
            if event.get("type") == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        parts.append(block["text"])
        return "\n".join(parts)

    def raw(self) -> str:
        return json.dumps(self.events, ensure_ascii=False)


def run_session(root: Path, turns: list) -> Transcript:
    transcript = Transcript()
    for i, turn in enumerate(turns):
        cmd = ["claude", "-p", turn, "--output-format", "stream-json", "--verbose",
               "--permission-mode", "acceptEdits"]
        if i:
            assert transcript.session_id, "no session id from the previous turn"
            cmd += ["--resume", transcript.session_id]
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                                timeout=TURN_TIMEOUT, env=dict(os.environ))
        transcript.add(result.stdout)
        assert result.returncode == 0, result.stderr[-2000:]
    return transcript


def git(root: Path, *args) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def changed_files(root: Path) -> list:
    tracked = git(root, "diff", "--name-only", "HEAD").splitlines()
    untracked = git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted(set(tracked + untracked))


def entries(root: Path, rel: str, text: str | None = None) -> dict:
    """Map each `## <ID>: …` entry to (heading, yaml block, body) in a collection file."""
    text = (root / rel).read_text() if text is None else text
    result = {}
    for match in re.finditer(r"^## ([A-Z]-\d+): .*?(?=^## |\Z)", text, re.M | re.S):
        block = match.group(0)
        heading, _, rest = block.partition("\n")
        yaml_part, _, body = rest.partition("```\n\n") if "```yaml" in rest else ("", "", rest)
        result[match.group(1)] = (heading, yaml_part, body.strip())
    return result


def collection_for(id_: str) -> str:
    return {"Q": "00-charter/questions.md", "H": "00-charter/hypotheses.md",
            "A": "00-charter/assumptions.md"}[id_[0]]


def status(root: Path) -> dict:
    result = subprocess.run([sys.executable, SCRIPT, "status"], cwd=root, capture_output=True, text=True)
    return json.loads(result.stdout)


def check_expectations(root: Path, transcript: Transcript, expect: dict) -> None:
    text = transcript.assistant_text()
    lower = text.lower()
    for path, needles in expect.get("files_contain", {}).items():
        content = (root / path).read_text()
        for needle in needles:
            assert needle in content, f"{path} should contain {needle!r}"
    for path, needles in expect.get("files_not_contain", {}).items():
        content = (root / path).read_text().lower()
        for needle in needles:
            assert needle.lower() not in content, f"{path} should not contain {needle!r}"
    for path, patterns in expect.get("files_match", {}).items():
        content = (root / path).read_text()
        for pattern in patterns:
            assert re.search(pattern, content, re.M), f"{path} should match {pattern!r}"
    items = {i["id"]: i for i in status(root)["items"]}
    for id_, want in expect.get("item_status", {}).items():
        assert id_ in items, f"{id_} missing"
        assert items[id_]["status"] == want, f"{id_} is {items[id_]['status']}, expected {want}"
    for id_, field_values in expect.get("item_fields", {}).items():
        for field, want in field_values.items():
            assert items[id_].get(field) == want, f"{id_}.{field}"
    for id_ in expect.get("absent_items", []):
        assert id_ not in items, f"{id_} should not exist"
    for path in expect.get("unchanged_files", []):
        assert path not in changed_files(root), f"{path} changed"
    for id_ in expect.get("entry_text_unchanged", []):
        rel = collection_for(id_)
        before = entries(root, rel, git(root, "show", f"HEAD:{rel}"))[id_]
        after = entries(root, rel)[id_]
        assert (before[0], before[2]) == (after[0], after[2]), f"{id_} title or text changed"
    for needle in expect.get("transcript_contains", []):
        assert needle.lower() in lower, f"transcript should mention {needle!r}"
    for needle in expect.get("transcript_not_contains", []):
        assert needle.lower() not in lower, f"transcript should not mention {needle!r}"
    charter = "\n".join((root / collection_for(p)).read_text() for p in "QHA")
    for needle in expect.get("charter_contains", []):
        assert needle in charter, f"charter entries should contain {needle!r}"
    for pattern, (low, high) in expect.get("charter_count", {}).items():
        count = len(re.findall(pattern, charter, re.M))
        assert low <= count <= high, f"{pattern!r} appears {count} times in the charter, expected {low}–{high}"
    for pattern, bounds in expect.get("transcript_count", {}).items():
        count = len(re.findall(pattern, text, re.I))
        low, high = bounds
        assert low <= count <= high, f"{pattern!r} appears {count} times, expected {low}–{high}"
    if "first_reply_contains" in expect:
        first = next((e for e in transcript.events if e.get("type") == "assistant"
                      and any(b.get("type") == "text" for b in e["message"]["content"])), None)
        first_text = " ".join(b["text"] for b in first["message"]["content"] if b.get("type") == "text")
        for needle in expect["first_reply_contains"]:
            assert needle.lower() in first_text.lower(), f"first reply should mention {needle!r}"


@pytest.mark.parametrize("path", SCENARIOS, ids=[p.stem for p in SCENARIOS])
def test_scenario(path, make_engagement):
    scenario = yaml.safe_load(path.read_text())
    root = make_engagement(scenario.get("fixture", "fresh"), scenario.get("model_use"),
                           scenario.get("edits", ()))
    transcript = run_session(root, scenario["turns"])

    check = subprocess.run([sys.executable, SCRIPT, "check"], cwd=root, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout

    for call in transcript.tool_calls():
        assert "10-sources/" not in json.dumps(call.get("input", {})), f"tool call touched 10-sources/: {call}"
    assert CANARY not in transcript.raw()
    for rel in changed_files(root):
        if (root / rel).is_file():
            assert CANARY not in (root / rel).read_text(errors="replace"), rel
    for rel in ("00-charter/questions.md", "00-charter/hypotheses.md", "00-charter/assumptions.md"):
        assert not re.search(r"^audience: client-ready", (root / rel).read_text(), re.M), rel

    check_expectations(root, transcript, scenario.get("expect", {}))
