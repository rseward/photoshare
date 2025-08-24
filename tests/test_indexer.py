

import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import indexing

@patch('app.database.get_db_connection')
@patch('app.indexing.Pool') # Mock the Pool class
def test_indexer_ignores_patterns(mock_pool, mock_get_db, tmp_path, monkeypatch):
    """
    Tests that the indexer correctly ignores files matching patterns
    in the specified ignore file.
    """
    # 1. Setup test environment
    photo_root = tmp_path / "photos"
    photo_root.mkdir()

    good_photo = photo_root / "good_photo.jpg"
    good_photo.touch()

    thumb_dir = photo_root / ".thumbnails"
    thumb_dir.mkdir()
    ignored_photo = thumb_dir / "thumb.jpg"
    ignored_photo.touch()

    ignore_file = tmp_path / "ignore.txt"
    ignore_file.write_text("**/.*/**\n")

    monkeypatch.setenv("PHOTOSHARE_PHOTO_DIRS", str(photo_root))
    monkeypatch.setenv("PHOTOSHARE_PHOTO_IGNORE_PATS", str(ignore_file))

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = []
    mock_get_db.return_value = mock_conn

    # Mock the instance of the Pool and its imap_unordered method
    mock_pool_instance = mock_pool.return_value.__enter__.return_value
    # This simulates that the pool returns no results, we check the jobs sent to it
    mock_pool_instance.imap_unordered.return_value = []

    # 2. Run the indexer
    indexing.run_indexing()

    # 3. Assert the results
    # Get the list of jobs that would have been sent to the pool
    jobs_sent_to_pool = mock_pool_instance.imap_unordered.call_args[0][1]
    processed_photos = [job[0] for job in jobs_sent_to_pool]

    assert len(processed_photos) == 1, "Should only attempt to process one photo"
    assert processed_photos[0] == good_photo, "The wrong photo was processed"
    assert ignored_photo not in processed_photos, "The ignored photo was processed"
