import os
import sys
import pytest
import sqlite3
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
import importlib

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules that will need reloading
from app import main, database

@pytest.fixture
def client_for_new_sequence(monkeypatch, tmp_path):
    """
    Creates a TestClient with a pre-populated, non-indexed database 
    specifically for testing the 'new' filter sequence.
    """
    db_path = tmp_path / "test_sequence.db"
    api_key = "test_key_sequence"
    
    monkeypatch.setenv("PHOTOSHARE_DATABASE_FILE", str(db_path))
    monkeypatch.setenv("PHOTOSHARE_API_KEY", api_key)
    
    # Create a dummy ignore file
    ignore_file = tmp_path / "ignore.txt"
    ignore_file.touch()
    monkeypatch.setenv("PHOTOSHARE_PHOTO_IGNORE_PATS", str(ignore_file))
    
    # Manually create and populate the database
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            geolocation TEXT,
            datetime_taken TEXT,
            datetime_added TEXT,
            tags TEXT,
            md5sum TEXT
        );
    """)

    # Insert test data with controlled timestamps
    now = datetime.now(timezone.utc)
    photo_data = [
        (1, "/fake/path1.jpg", 100, 100, (now - timedelta(days=2)).isoformat()), # Oldest
        (2, "/fake/path2.jpg", 100, 100, (now - timedelta(days=1)).isoformat()), # Middle
        (3, "/fake/path3.jpg", 100, 100, now.isoformat())  # Newest
    ]
    
    conn.executemany(
        "INSERT INTO photos (id, path, width, height, datetime_added) VALUES (?, ?, ?, ?, ?)",
        photo_data
    )
    conn.commit()
    conn.close()

    # Reload modules to use the patched environment
    importlib.reload(database)
    importlib.reload(main)

    with TestClient(main.app) as client:
        yield client, api_key

def test_get_new_photos_returns_correct_sequence(client_for_new_sequence):
    """
    Tests that the slideshow for 'new' photos navigates in chronological order (newest to oldest).
    Note: Initial load randomly selects from top 1000, so we start from a known photo.
    """
    client, api_key = client_for_new_sequence
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Expected order when navigating from photo 3: 3 -> 2 -> 1 -> (wraparound to 3)
    # Photo 3 is the newest, then 2, then 1 (oldest)

    # Start from the newest photo (ID 3) explicitly
    current_photo_id = 3
    actual_ids = [current_photo_id]

    # Navigate forward (next should go to older photos: 3 -> 2 -> 1)
    url = f"/photos/sequence/new?direction=next&current_photo_id={current_photo_id}"
    response = client.get(url, headers=headers)
    assert response.status_code == 200, f"Navigation failed: {response.text}"

    photo_data = response.json()
    actual_ids.append(photo_data['id'])
    assert photo_data['id'] == 2, f"After photo 3, should get photo 2, but got {photo_data['id']}"
    current_photo_id = photo_data['id']

    # Navigate forward again (2 -> 1)
    url = f"/photos/sequence/new?direction=next&current_photo_id={current_photo_id}"
    response = client.get(url, headers=headers)
    assert response.status_code == 200, f"Navigation failed: {response.text}"

    photo_data = response.json()
    actual_ids.append(photo_data['id'])
    assert photo_data['id'] == 1, f"After photo 2, should get photo 1, but got {photo_data['id']}"

    # Verify we got the correct chronological sequence
    assert actual_ids == [3, 2, 1], f"Expected chronological sequence [3, 2, 1], got {actual_ids}"