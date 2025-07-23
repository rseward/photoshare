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
    
    # Manually create and populate the database
    conn = sqlite3.connect(db_path)
    database.init_db() # Ensures schema is created

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
    Tests that the slideshow for 'new' photos returns the entire sequence
    of photos in the correct order (newest to oldest).
    """
    client, api_key = client_for_new_sequence
    headers = {"Authorization": f"Client-ID {api_key}"}
    
    # Expected order of photo IDs: 3 (newest), 2, 1 (oldest)
    expected_ids = [3, 2, 1]
    actual_ids = []
    
    # 1. Fetch the first photo (should be the newest)
    response = client.get("/photos/sequence/new", headers=headers)
    assert response.status_code == 200, f"Initial request failed: {response.text}"
    
    photo_data = response.json()
    actual_ids.append(photo_data['id'])
    current_photo_id = photo_data['id']

    # 2. Fetch the rest of the sequence
    for _ in range(len(expected_ids) - 1):
        url = f"/photos/sequence/new?direction=next&current_photo_id={current_photo_id}"
        response = client.get(url, headers=headers)
        assert response.status_code == 200, f"Sequential request failed: {response.text}"
        
        photo_data = response.json()
        actual_ids.append(photo_data['id'])
        current_photo_id = photo_data['id']

    # 3. Verify the entire sequence is correct
    assert actual_ids == expected_ids, f"The returned sequence {actual_ids} did not match the expected sequence {expected_ids}."
