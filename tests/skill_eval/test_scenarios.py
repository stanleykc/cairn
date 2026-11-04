"""Run each scripted scenario in `scenarios/*.yaml` against a live model (opt-in, R20).

Scenario keys:
- `name`: shown in the test id.
- `fixture`: `fresh`, or the name of a folder in `tests/fixtures/charter/`.
- `model_use` (optional): force the policy in both files before the run.
- `edits` (optional): `[path, old, new]` text replacements made before the first commit.
- `turns`: the consultant's messages; the first one usually starts with `/charter`.
- `expect`: per-scenario assertions (see `check_expectations`).

Set `CAIRN_SKILL_EVAL_OUT=<folder>` to save each scenario's transcript and `git diff` there
for review by hand (synthetic data only).

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
# A skill's `allowed-tools` cover only the turn that invoked it. In a real engagement the
# `.claude/settings.json` that `cairn init` ships allows the helper on later turns, but Claude
# Code applies project allow rules only after the folder is trusted, and `claude -p` never
# shows the trust dialog. So the same rule is passed on every call, as the docs recommend for
# `-p`; `Transcript.denials()` still fails the scenario if a helper call is ever refused.
ALLOW_HELPER = "Bash(python3 *charter.py*)"


class Transcript:
    def __init__(self):
        self.events: list = []
        self.session_id: str | None = None
        self.turns: list = []  # (consultant message, index of its first event)

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

    def denials(self) -> list:
        """Tool results that say a call was refused for lack of permission."""
        found = []
        for event in self.events:
            if event.get("type") != "user":
                continue
            content = event.get("message", {}).get("content", [])
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_result":
                    text = json.dumps(block.get("content"), ensure_ascii=False)
                    if block.get("is_error") and ("requires approval" in text
                                                  or "permission to use" in text):
                        found.append(text[:200])
        return found

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


def run_session(root: Path, turns: list, transcript: Transcript) -> Transcript:
    for i, turn in enumerate(turns):
        transcript.turns.append((turn, len(transcript.events)))
        cmd = ["claude", "-p", turn, "--output-format", "stream-json", "--verbose",
               "--permission-mode", "acceptEdits", "--allowedTools", ALLOW_HELPER]
        if i:
            assert transcript.session_id, "no session id from the previous turn"
            cmd += ["--resume", transcript.session_id]
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                                timeout=TURN_TIMEOUT, env=dict(os.environ))
        transcript.add(result.stdout)
        assert result.returncode == 0, result.stderr[-2000:]
    return transcript


def save_report(name: str, root: Path, transcript: Transcript) -> None:
    out = os.environ.get("CAIRN_SKILL_EVAL_OUT")
    if not out:
        return
    lines = [f"# {name}", ""]
    bounds = [start for _, start in transcript.turns] + [len(transcript.events)]
    for n, (message, start) in enumerate(transcript.turns):
        lines += [f"## Turn {n + 1}", "", f"**Consultant:** {message}", ""]
        for event in transcript.events[start : bounds[n + 1]]:
            if event.get("type") != "assistant":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    lines += [f"**Claude:** {block['text']}", ""]
                elif block.get("type") == "tool_use":
                    detail = json.dumps(block.get("input", {}), ensure_ascii=False)
                    lines += [f"- tool `{block.get('name')}`: {detail[:300]}", ""]
    lines += ["## git diff", "", "```diff", git(root, "diff", "HEAD"), "```", "",
              "## untracked", "", git(root, "ls-files", "--others", "--exclude-standard")]
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text("\n".join(lines))


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
    transcript = Transcript()
    try:
        run_session(root, scenario["turns"], transcript)
    finally:
        save_report(path.stem, root, transcript)

    check = subprocess.run([sys.executable, SCRIPT, "check"], cwd=root, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout

    assert transcript.denials() == [], "a tool call was refused for lack of permission"
    for call in transcript.tool_calls():
        assert "10-sources/" not in json.dumps(call.get("input", {})), f"tool call touched 10-sources/: {call}"
    assert CANARY not in transcript.raw()
    for rel in changed_files(root):
        if (root / rel).is_file():
            assert CANARY not in (root / rel).read_text(errors="replace"), rel
    for rel in ("00-charter/questions.md", "00-charter/hypotheses.md", "00-charter/assumptions.md"):
        assert not re.search(r"^audience: client-ready", (root / rel).read_text(), re.M), rel

    check_expectations(root, transcript, scenario.get("expect", {}))
