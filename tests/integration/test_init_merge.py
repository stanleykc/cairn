import json

from cairn import layout
from conftest import ACME, LEAD, run_cairn, tree_hash

MERGE_ARGS = ("--engagement", "X", "--client", ACME, "--lead", LEAD, "--no-git")


def make_existing(tmp_path):
    existing = tmp_path / "existing"
    (existing / "10-sources" / "raw").mkdir(parents=True)
    (existing / "10-sources" / "raw" / "brief.pdf").write_text("orig")
    (existing / "README.md").write_text("# mine")
    (existing / "_templates").mkdir()
    (existing / "_templates" / "finding.md").write_text("my finding template")
    return existing


def test_merge_keeps_existing_files(tmp_path, git_env):
    existing = make_existing(tmp_path)
    before = tree_hash(existing)
    result = run_cairn("init", existing, "--merge", *MERGE_ARGS, cwd=tmp_path, env=git_env)
    assert result.returncode == 0, result.stderr

    after = tree_hash(existing)
    for rel, digest in before.items():
        assert after[rel] == digest, rel  # SC-004

    skipped = result.stdout.split("Skipped (already present):")[1].split("Next steps:")[0]
    for rel in ("README.md", "10-sources/raw/brief.pdf", "_templates/finding.md"):
        assert f"  {rel}\n" in skipped

    assert sorted(p.name for p in (existing / "10-sources" / "raw").iterdir()) == ["brief.pdf"]
    for rel in layout.CANONICAL_FOLDERS:
        assert (existing / rel).is_dir(), rel
    for rel in layout.SEED_FILES:
        assert (existing / rel).is_file(), rel

    manifest = json.loads((existing / ".cairn" / "manifest.json").read_text())
    assert "_templates/finding.md" not in manifest["files"]
    assert "_templates/observation.md" in manifest["files"]


def test_without_merge_refused(tmp_path, git_env):
    existing = make_existing(tmp_path)
    before = tree_hash(existing)
    result = run_cairn("init", existing, *MERGE_ARGS, cwd=tmp_path, env=git_env)
    assert result.returncode == 1
    assert "--merge" in result.stderr
    assert tree_hash(existing) == before
    assert not (existing / ".cairn").exists()


def test_merge_into_engagement_points_to_refresh(tmp_path, git_env):
    eng = tmp_path / "eng"
    assert run_cairn("init", eng, *MERGE_ARGS, cwd=tmp_path, env=git_env).returncode == 0
    before = tree_hash(eng)
    result = run_cairn("init", eng, "--merge", *MERGE_ARGS, cwd=tmp_path, env=git_env)
    assert result.returncode == 1
    assert "cairn refresh" in result.stderr
    assert tree_hash(eng) == before
