import os
import sys
import pytest
from click.testing import CliRunner
from pathlib import Path
import shutil
import sqlite3

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from indexer import cli

@pytest.fixture(scope="session")
def sample_photos_path():
    """Returns the absolute path to the sample_photos directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sample_photos'))

def test_indexer_cli_success(monkeypatch, tmp_path, sample_photos_path):
    """
    Tests that the 'indexer.py index' command runs successfully.
    """
    db_path = tmp_path / "test_cli.db"
    monkeypatch.setenv("PHOTOSHARE_DATABASE_FILE", str(db_path))
    monkeypatch.setenv("PHOTOSHARE_PHOTO_DIRS", sample_photos_path)
    monkeypatch.setenv("PHOTOSHARE_PHOTO_IGNORE_PATS", "")

    runner = CliRunner()
    result = runner.invoke(cli, ['index'])

    assert result.exit_code == 0
    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
    conn.close()
    assert count == 1

def test_indexer_with_ignore_pattern(monkeypatch, tmp_path, sample_photos_path):
    """
    Tests that the indexer correctly ignores files based on a pattern.
    """
    # Create a new directory for this test to avoid side effects
    test_photo_dir = tmp_path / "test_photos"
    shutil.copytree(sample_photos_path, test_photo_dir)

    # Create a new photo in a subdirectory that should be ignored
    ignored_subdir = test_photo_dir / ".thumbcache"
    ignored_subdir.mkdir()
    (ignored_subdir / "ignored_photo.png").touch()

    # Create the ignore file with the problematic pattern
    ignore_file = tmp_path / "ignore.txt"
    with open(ignore_file, "w") as f:
        f.write("*/.thumbcache/*\n")

    db_path = tmp_path / "test_ignore.db"
    monkeypatch.setenv("PHOTOSHARE_DATABASE_FILE", str(db_path))
    monkeypatch.setenv("PHOTOSHARE_PHOTO_DIRS", str(test_photo_dir))
    monkeypatch.setenv("PHOTOSHARE_PHOTO_IGNORE_PATS", str(ignore_file))

    runner = CliRunner()
    result = runner.invoke(cli, ['index'])
    assert result.exit_code == 0

    # Check that the ignored photo was NOT indexed, but the original one was
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM photos WHERE path LIKE ?", ('%placeholder.png',))
    assert cursor.fetchone() is not None, "The original photo should be indexed."
    cursor.execute("SELECT id FROM photos WHERE path LIKE ?", ('%ignored_photo.png',))
    assert cursor.fetchone() is None, "The ignored photo should NOT be indexed."
    conn.close()

def test_indexer_cli_lock_file_exists(monkeypatch, tmp_path):
    """
    Tests that the indexer aborts if a lock file already exists.
    """
    db_path = tmp_path / "test_lock.db"
    lock_file = tmp_path / "index.lock"
    lock_file.touch()

    monkeypatch.setenv("PHOTOSHARE_DATABASE_FILE", str(db_path))

    runner = CliRunner()
    result = runner.invoke(cli, ['index'])

    assert result.exit_code == 1
    assert "Lock file exists" in result.output