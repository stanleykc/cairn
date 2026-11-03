import pytest

from cairn.transaction import Transaction


def test_rollback_removes_created_files_and_folders(tmp_path):
    with pytest.raises(RuntimeError):
        with Transaction() as tx:
            tx.mkdir(tmp_path / "a")
            tx.mkdir(tmp_path / "a" / "b")
            tx.write_bytes(tmp_path / "a" / "b" / "f.md", b"x")
            tx.write_bytes(tmp_path / "a" / "g.md", b"y")
            raise RuntimeError("boom")
    assert list(tmp_path.iterdir()) == []


def test_pre_existing_paths_survive(tmp_path):
    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "old.txt").write_text("old")
    with pytest.raises(RuntimeError):
        with Transaction() as tx:
            assert tx.mkdir(tmp_path / "keep") is False
            tx.write_bytes(tmp_path / "keep" / "new.txt", b"new")
            raise RuntimeError("boom")
    assert sorted(p.name for p in (tmp_path / "keep").iterdir()) == ["old.txt"]
    assert (tmp_path / "keep" / "old.txt").read_text() == "old"


def test_write_bytes_never_overwrites(tmp_path):
    existing = tmp_path / "f.md"
    existing.write_text("mine")
    tx = Transaction()
    with pytest.raises(FileExistsError):
        tx.write_bytes(existing, b"theirs")
    tx.rollback()
    assert existing.read_text() == "mine"


def test_folder_with_unrecorded_file_is_kept(tmp_path):
    with pytest.raises(RuntimeError):
        with Transaction() as tx:
            tx.mkdir(tmp_path / "a")
            (tmp_path / "a" / "someone-else.txt").write_text("x")
            raise RuntimeError("boom")
    assert (tmp_path / "a" / "someone-else.txt").exists()


def test_keyboard_interrupt_rolls_back_and_reraises(tmp_path):
    with pytest.raises(KeyboardInterrupt):
        with Transaction() as tx:
            tx.mkdir(tmp_path / "a")
            tx.write_bytes(tmp_path / "a" / "f", b"x")
            raise KeyboardInterrupt
    assert not (tmp_path / "a").exists()


def test_git_dir_removed_on_rollback(tmp_path):
    with pytest.raises(RuntimeError):
        with Transaction() as tx:
            tx.mkdir(tmp_path / "e")
            tx.mark_git_created(tmp_path / "e" / ".git")
            (tmp_path / "e" / ".git" / "objects").mkdir(parents=True)
            (tmp_path / "e" / ".git" / "HEAD").write_text("ref")
            raise RuntimeError("boom")
    assert not (tmp_path / "e").exists()


def test_rollback_tolerates_missing_paths(tmp_path):
    tx = Transaction()
    tx.mkdir(tmp_path / "a")
    tx.write_bytes(tmp_path / "a" / "f", b"x")
    (tmp_path / "a" / "f").unlink()
    tx.rollback()
    assert not (tmp_path / "a").exists()
