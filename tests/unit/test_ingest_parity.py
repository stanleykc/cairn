"""`ingest.py` copies charter.py's parsing code (003 research R3); both must behave identically."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "src" / "cairn" / "assets" / "skills"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ingest = _load("parity_ingest", SKILLS / "ingest" / "scripts" / "ingest.py")
charter = _load("parity_charter", SKILLS / "charter" / "scripts" / "charter.py")

VALUES = [
    "", "   ", "# only a comment", "plain", "plain # comment", "plain#not-a-comment",
    '"quoted"', '"quoted" # comment', '"quoted" trailing', '"esc \\" aped"', '"bad \\q escape"',
    "'single'", "'it''s'", "'unterminated", '"unterminated',
    "[]", '["S-001", "S-002"]', "[S-001, S-002]", "['a', \"b\"]", '["a, b", c]', "[a, [b]]",
    "[a, {b: c}]", "[unterminated", "[a] trailing", "[a] # ok", "{a: b}", "true", "0", "2026-11-05",
]

MAPPINGS = [
    ["id: \"S-001\"", "type: source", "status: proposed  # comment"],
    ["supports:", "  - \"O-001\"", "  - O-002", "title: x"],
    ["attendees: []", "uncertain_passages: [\"p. 3\", \"§ A > B\"]"],
    ["not a key line", "ok: yes"],
    ["list:", "  - [nested]", "after: 1"],
    ["", "# comment", "key:"],
    ["bad: \"unterminated", "good: 1"],
]

FILES = [
    "---\nid: \"S-001\"\ntype: source\n---\n\n## Context\n",
    "no front matter\n",
    "---\nunclosed: true\n",
    "---\ntype: questions\n---\n\n## Q-001: Why?\n\n```yaml\nid: \"Q-001\"\nstatus: proposed\n```\n",
    "---\n---\n\n## Q-1: bad\n\n```yaml\nid: Q-1\n```\n\n## Q-002 no colon\n",
    "---\na: [x\n---\n\n## H-001: open fence\n\n```yaml\nid: H-001\n",
]


@pytest.mark.parametrize("raw", VALUES)
def test_parse_value(raw):
    assert ingest.parse_value(raw) == charter.parse_value(raw)


@pytest.mark.parametrize("lines", MAPPINGS)
def test_parse_mapping(lines):
    assert ingest.parse_mapping(lines, 2) == charter.parse_mapping(lines, 2)


@pytest.mark.parametrize("text", FILES)
def test_split_front_matter_and_parse_file(text):
    lines = text.splitlines()
    assert ingest.split_front_matter(lines) == charter.split_front_matter(lines)
    assert ingest.parse_file(text, "x.md") == charter.parse_file(text, "x.md")


def _engagement(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "engagement.md").write_text("---\ntype: engagement\nid: test\n---\n")
    return folder


def _find(module, *args, **kwargs):
    try:
        return "ok", module.find_root(*args, **kwargs)
    except module.Fail as exc:
        return "fail", exc.code


def test_find_root(tmp_path):
    outer = _engagement(tmp_path / "outer")
    inner = _engagement(outer / "nested" / "inner")
    deep = inner / "30-observations" / "x"
    deep.mkdir(parents=True)
    script = inner / ".claude" / "skills" / "s" / "scripts" / "s.py"
    script.parent.mkdir(parents=True)
    script.write_text("")
    nowhere = tmp_path / "nowhere"
    nowhere.mkdir()
    cases = [
        ((None,), {"cwd": deep}),
        ((None,), {"cwd": outer / "nested"}),
        ((str(inner),), {}),
        ((str(nowhere),), {}),
        ((None,), {"cwd": nowhere, "script_path": script}),
        ((None,), {"cwd": nowhere, "script_path": nowhere / "x.py"}),
    ]
    for args, kwargs in cases:
        got_i, got_c = _find(ingest, *args, **kwargs), _find(charter, *args, **kwargs)
        assert got_i[0] == got_c[0], (args, kwargs)
        if got_i[0] == "ok":
            assert got_i[1] == got_c[1]
        else:
            assert got_i[1] == got_c[1] == 2


def test_shared_helpers_identical():
    """The copied helpers' source text matches, so a fix to one is a fix to both."""
    import inspect

    for name in ("_find_close_quote", "_rest_ok", "parse_value", "parse_mapping", "split_front_matter",
                 "parse_file", "as_list", "read_text", "is_engagement", "append_changelog", "atomic_write"):
        assert inspect.getsource(getattr(ingest, name)) == inspect.getsource(getattr(charter, name)), name
