"""Run each scripted scenario in `scenarios/<skill>/*.yaml` against a live model (opt-in).

Common scenario keys:
- `name`: shown in the test id.
- `fixture`: `fresh`, a folder in `tests/fixtures/charter/` (charter), or
  `tests/fixtures/ingest/golden/<name>` (ingest).
- `model_use` (optional): force the policy in both files before the run.
- `turns`: the consultant's messages; the first one usually starts with `/<skill>`. An
  ingest turn may also be a mapping `{say: "...", new_session: true, add_raw: [names]}`.
- `expect`: per-scenario assertions (see `check_expectations` and `check_ingest`).

Charter keys: `edits` (`[path, old, new]` replacements made before the first commit).
Ingest keys: `model_use_notes`, `code_name`, `raw` (MAKE registry names written into
`10-sources/raw/`), `raw_files` (name → text, for canaries), `outside_files`, `canaries`, `hide_poppler`.

Set `CAIRN_SKILL_EVAL_OUT=<folder>` to save each scenario's transcript and `git diff` there
for review by hand (synthetic data only).

Every scenario also runs its skill's "always" assertions (`ALWAYS`):
- charter: `charter.py check` exits 0; no tool call names a path under `10-sources/`; the
  canary never appears in the transcript or in any changed file; no charter item is
  `client-ready`.
- ingest: every file under `10-sources/raw/` has the same SHA-256 before and after (SC-001);
  `ingest.py verify` exits 0; no file has `audience: client-ready`; no listed canary appears
  in the transcript or in any file changed outside `raw/` (SC-002).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from .conftest import write_raw

HERE = Path(__file__).resolve().parent
CANARY = "CANARY-7f3a"  # same as conftest.CANARY
SCENARIOS = sorted((HERE / "scenarios").glob("*/*.yaml"))
SCRIPT = ".claude/skills/charter/scripts/charter.py"
INGEST_SCRIPT = ".claude/skills/ingest/scripts/ingest.py"
TURN_TIMEOUT = 900
# A skill's `allowed-tools` cover only the turn that invoked it. In a real engagement the
# `.claude/settings.json` that `cairn init` ships allows the helper on later turns, but Claude
# Code applies project allow rules only after the folder is trusted, and `claude -p` never
# shows the trust dialog. So the same rule is passed on every call, as the docs recommend for
# `-p`; `Transcript.denials()` still fails the scenario if a helper call is ever refused.
ALLOW_HELPER = "Bash(python3 *charter.py*)"
ALLOW = {"charter": ALLOW_HELPER, "ingest": "Bash(python3 *ingest.py*)"}
POPPLER = ("pdftotext", "pdfinfo", "pdfimages")


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


def path_without_poppler() -> str:
    """PATH minus every folder that holds a poppler tool (R4 unchecked mode)."""
    hidden = {str(Path(shutil.which(t)).parent) for t in POPPLER if shutil.which(t)}
    return os.pathsep.join(d for d in os.environ.get("PATH", "").split(os.pathsep) if d not in hidden)


def run_session(root: Path, turns: list, transcript: Transcript, skill: str = "charter",
                env=None, on_turn=None) -> Transcript:
    resume = False
    for turn in turns:
        if isinstance(turn, dict):
            if on_turn:
                on_turn(turn)
            if turn.get("new_session"):
                resume = False
            turn = turn["say"]
        transcript.turns.append((turn, len(transcript.events)))
        cmd = ["claude", "-p", turn, "--output-format", "stream-json", "--verbose",
               "--permission-mode", "acceptEdits", "--allowedTools", ALLOW[skill]]
        if resume:
            assert transcript.session_id, "no session id from the previous turn"
            cmd += ["--resume", transcript.session_id]
        resume = True
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                                timeout=TURN_TIMEOUT, env=env or dict(os.environ))
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


def charter_always(root: Path, transcript: Transcript, scenario: dict, before: dict) -> None:
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


# --- ingest ------------------------------------------------------------------------


def raw_hashes(root: Path) -> dict:
    raw = root / "10-sources" / "raw"
    result = {}
    for path in sorted(raw.rglob("*")):
        if path.is_file():
            try:
                result[path.relative_to(raw).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            except PermissionError:  # a restricted original made unreadable on purpose
                result[path.relative_to(raw).as_posix()] = "unreadable"
    return result


def ingest_json(root: Path, *args) -> tuple:
    result = subprocess.run([sys.executable, INGEST_SCRIPT, *args], cwd=root, capture_output=True, text=True)
    try:
        return result.returncode, json.loads(result.stdout)
    except ValueError:
        return result.returncode, {"stdout": result.stdout, "stderr": result.stderr}


def ingest_always(root: Path, transcript: Transcript, scenario: dict, before: dict) -> None:
    assert raw_hashes(root) == before["raw"], "a file under 10-sources/raw/ changed (SC-001)"
    code, report = ingest_json(root, "verify")
    assert code == 0, report
    assert transcript.denials() == [], "a tool call was refused for lack of permission"
    for path in root.rglob("*.md"):
        if ".git" in path.parts:
            continue
        assert not re.search(r"^audience: client-ready", path.read_text(errors="replace"), re.M), path
    raw_text = transcript.raw()
    for canary in scenario.get("canaries", []):
        assert canary not in raw_text, f"canary {canary} reached the session (SC-002)"
        for rel in changed_files(root):
            if rel.startswith("10-sources/raw/") or not (root / rel).is_file():
                continue
            assert canary not in (root / rel).read_text(errors="replace"), (canary, rel)


def sources_by_raw(root: Path) -> dict:
    code, report = ingest_json(root, "status")
    assert code == 0, report
    result = {}
    for source in report["sources"]:
        path = root / "10-sources" / "extracted" / f"{source['id']}.md"
        text = path.read_text()
        front = yaml.safe_load(text.split("---\n")[1])
        result[source["raw_file"]] = {"front": front, "text": text, "id": source["id"]}
    return result


def check_ingest(root: Path, transcript: Transcript, expect: dict) -> None:
    """Ingest expectations, keyed by the original's path in `raw/`."""
    sources = sources_by_raw(root)
    if "source_count" in expect:
        assert len(sources) == expect["source_count"], sorted(sources)
    for raw, want in expect.get("sources", {}).items():
        if want is None:
            assert raw not in sources, f"{raw} should have no source"
            continue
        assert raw in sources, f"no source for {raw}"
        source = sources[raw]
        for field, value in want.get("fields", {}).items():
            assert source["front"].get(field) == value, f"{raw}: {field} is {source['front'].get(field)!r}"
        for needle in want.get("contains", []):
            assert needle in source["text"], f"{raw} should contain {needle!r}"
        for needle in want.get("not_contains", []):
            assert needle not in source["text"], f"{raw} should not contain {needle!r}"
        for pattern in want.get("matches", []):
            assert re.search(pattern, source["text"], re.M), f"{raw} should match {pattern!r}"
        for locator in want.get("uncertain_includes", []):
            assert any(locator in u for u in source["front"].get("uncertain_passages") or []), (raw, locator)
    index = (root / "10-sources" / "index.md").read_text()
    if "index_rows" in expect:
        rows = re.findall(r"^\| S-\d+ \|", index, re.M)
        assert len(rows) == expect["index_rows"], index
    for pattern in expect.get("index_matches", []):
        assert re.search(pattern, index, re.M), f"index should match {pattern!r}"
    for needle in expect.get("index_not_contains", []):
        assert needle.lower() not in index.lower(), f"index should not contain {needle!r}"
    changelog = (root / "60-log" / "changelog.md").read_text()
    for pattern in expect.get("changelog_matches", []):
        assert re.search(pattern, changelog, re.M), f"changelog should match {pattern!r}"
    for pattern, (low, high) in expect.get("changelog_count", {}).items():
        count = len(re.findall(pattern, changelog, re.M))
        assert low <= count <= high, f"{pattern!r} appears {count} times in the changelog"
    if expect.get("nothing_written"):
        assert changed_files(root) == [], changed_files(root)
    for path in expect.get("unchanged_files", []):
        assert path not in changed_files(root), f"{path} changed"
    for name in expect.get("never_read", []):
        for call in transcript.tool_calls():
            if call.get("name") in ("Read", "Grep", "Glob") or call.get("name") == "Bash":
                detail = json.dumps(call.get("input", {}))
                if call.get("name") == "Bash" and "ingest.py" in detail:
                    continue
                assert f"raw/{name}" not in detail, f"a tool call opened raw/{name}: {call}"
    if expect.get("no_raw_reads"):
        for call in transcript.tool_calls():
            detail = json.dumps(call.get("input", {}))
            if call.get("name") == "Bash" and "ingest.py" in detail:
                continue
            assert "10-sources/raw" not in detail, f"a tool call touched raw/: {call}"
    text = transcript.assistant_text().lower()
    for needle in expect.get("transcript_contains", []):
        assert needle.lower() in text, f"transcript should mention {needle!r}"
    for needle in expect.get("transcript_not_contains", []):
        assert needle.lower() not in text, f"transcript should not mention {needle!r}"
    for pattern, (low, high) in expect.get("transcript_count", {}).items():
        count = len(re.findall(pattern, text, re.I))
        assert low <= count <= high, f"{pattern!r} appears {count} times, expected {low}–{high}"


ALWAYS = {"charter": charter_always, "ingest": ingest_always}


@pytest.mark.parametrize("path", SCENARIOS, ids=[f"{p.parent.name}/{p.stem}" for p in SCENARIOS])
def test_scenario(path, request):
    skill = path.parent.name
    scenario = yaml.safe_load(path.read_text())
    env = dict(os.environ)
    if skill == "charter":
        root = request.getfixturevalue("make_engagement")(
            scenario.get("fixture", "fresh"), scenario.get("model_use"), scenario.get("edits", ()))
    else:
        root = request.getfixturevalue("make_ingest_engagement")(scenario)
        if scenario.get("hide_poppler"):
            env["PATH"] = path_without_poppler()
    before = {"raw": raw_hashes(root)} if skill == "ingest" else {}

    def on_turn(turn: dict) -> None:
        if turn.get("add_raw"):
            write_raw(root, turn["add_raw"])
            before["raw"] = raw_hashes(root)

    transcript = Transcript()
    try:
        run_session(root, scenario["turns"], transcript, skill, env, on_turn)
    finally:
        save_report(f"{skill}-{path.stem}", root, transcript)

    ALWAYS[skill](root, transcript, scenario, before)
    if skill == "charter":
        check_expectations(root, transcript, scenario.get("expect", {}))
    else:
        check_ingest(root, transcript, scenario.get("expect", {}))
