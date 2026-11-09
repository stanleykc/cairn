"""`ingest.py` copies charter.py's parsing code (003 research R3), and `observe.py` copies
ingest.py's parsing and content-unit code (005 research R3); all must behave identically."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "src" / "cairn" / "assets" / "skills"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # inspect.getsource needs it to find classes
    spec.loader.exec_module(module)
    return module


ingest = _load("parity_ingest", SKILLS / "ingest" / "scripts" / "ingest.py")
charter = _load("parity_charter", SKILLS / "charter" / "scripts" / "charter.py")
observe = _load("parity_observe", SKILLS / "extract-observations" / "scripts" / "observe.py")
INGEST_GOLDEN = REPO / "tests" / "fixtures" / "ingest" / "golden"
EXPECTED_SOURCES = sorted(INGEST_GOLDEN.glob("*/expected/S-*.md")) + sorted(INGEST_GOLDEN.glob("*/10-sources/extracted/S-*.md"))

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
    assert ingest.parse_value(raw) == charter.parse_value(raw) == observe.parse_value(raw)


@pytest.mark.parametrize("lines", MAPPINGS)
def test_parse_mapping(lines):
    assert ingest.parse_mapping(lines, 2) == charter.parse_mapping(lines, 2) == observe.parse_mapping(lines, 2)


@pytest.mark.parametrize("text", FILES)
def test_split_front_matter_and_parse_file(text):
    lines = text.splitlines()
    assert ingest.split_front_matter(lines) == charter.split_front_matter(lines) == observe.split_front_matter(lines)
    assert ingest.parse_file(text, "x.md") == charter.parse_file(text, "x.md") == observe.parse_file(text, "x.md")


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
        got_o = _find(observe, *args, **kwargs)
        assert got_i[0] == got_c[0] == got_o[0], (args, kwargs)
        if got_i[0] == "ok":
            assert got_i[1] == got_c[1] == got_o[1]
        else:
            assert got_i[1] == got_c[1] == got_o[1] == 2


def test_shared_helpers_identical():
    """The copied helpers' source text matches, so a fix to one is a fix to both."""
    import inspect

    for name in ("_find_close_quote", "_rest_ok", "parse_value", "parse_mapping", "split_front_matter",
                 "parse_file", "as_list", "read_text", "is_engagement", "append_changelog", "atomic_write"):
        assert inspect.getsource(getattr(ingest, name)) == inspect.getsource(getattr(charter, name)), name


def test_observe_helpers_identical_to_ingest():
    """observe.py's copies of the parsing, source and content-unit helpers match ingest.py's text."""
    import inspect

    for name in ("_find_close_quote", "_rest_ok", "parse_value", "parse_mapping", "split_front_matter",
                 "parse_file", "as_list", "read_text", "is_engagement", "find_root", "append_changelog",
                 "atomic_write", "_str", "_bool", "_int", "Source", "source_kind", "normalize", "Unit",
                 "split_units", "unit_words", "callouts", "uncertain_section", "speaker_labels"):
        assert inspect.getsource(getattr(observe, name)) == inspect.getsource(getattr(ingest, name)), name


def _units(module, path):
    src = module.Source(path, path.name, path.read_text())
    kind = module.source_kind(src)
    norm = module.normalize(src.content_lines(), src.content_first_line())
    units = module.split_units(norm, kind)
    return kind, norm, [(u.key, u.locator, u.line, u.header, u.body) for u in units]


@pytest.mark.parametrize("path", EXPECTED_SOURCES, ids=[f"{p.parts[-3]}/{p.name}" for p in EXPECTED_SOURCES])
def test_units_identical_to_ingest(path):
    """Same normalisation and unit split on every golden source (PDF, Word, markdown, text, transcript)."""
    assert _units(observe, path) == _units(ingest, path)
    src_o = observe.Source(path, path.name, path.read_text())
    src_i = ingest.Source(path, path.name, path.read_text())
    assert observe.callouts(src_o) == ingest.callouts(src_i)
    assert observe.speaker_labels(src_o) == ingest.speaker_labels(src_i)
    assert observe.uncertain_section(src_o) == ingest.uncertain_section(src_i)


def test_golden_sources_cover_every_kind():
    kinds = {observe.source_kind(observe.Source(p, p.name, p.read_text())) for p in EXPECTED_SOURCES}
    types = {observe.Source(p, p.name, p.read_text()).f("source_type") for p in EXPECTED_SOURCES}
    assert kinds >= {"pdf", "doc", "turns"} and types >= {"pdf", "docx", "markdown", "vtt"}
