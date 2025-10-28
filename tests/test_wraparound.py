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
def client_for_wraparound(monkeypatch, tmp_path):
    """
    Creates a TestClient with a small set of photos for testing wraparound.
    """
    db_path = tmp_path / "test_wraparound.db"
    api_key = "test_key_wraparound"

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

    # Insert small set of test data
    now = datetime.now(timezone.utc)
    photo_data = [
        # ID, path, width, height, datetime_added, tags
        (1, "/fake/path1.jpg", 100, 100, (now - timedelta(days=2)).isoformat(), "tag1"),
        (2, "/fake/path2.jpg", 100, 100, (now - timedelta(days=1)).isoformat(), None),  # untagged
        (3, "/fake/path3.jpg", 100, 100, now.isoformat(), "tag2"),
    ]

    conn.executemany(
        "INSERT INTO photos (id, path, width, height, datetime_added, tags) VALUES (?, ?, ?, ?, ?, ?)",
        photo_data
    )
    conn.commit()
    conn.close()

    # Reload modules to use the patched environment
    importlib.reload(database)
    importlib.reload(main)

    with TestClient(main.app) as client:
        yield client, api_key

def test_shuffle_wraparound_forward(client_for_wraparound):
    """
    Tests that plain shuffle wraps around when navigating forward from the last photo.
    """
    client, api_key = client_for_wraparound
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Use a fixed shuffle_id for deterministic ordering
    shuffle_id = 123

    # Start at the beginning
    response = client.get(f"/photos/sequence/shuffle?shuffle_id={shuffle_id}", headers=headers)
    assert response.status_code == 200
    first_photo_id = response.json()['id']

    # Navigate through all photos to reach the end
    current_id = first_photo_id
    seen_ids = [current_id]

    for _ in range(5):  # More iterations than photos to ensure wraparound
        url = f"/photos/sequence/shuffle?direction=next&current_photo_id={current_id}&shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        assert response.status_code == 200

        photo_data = response.json()
        current_id = photo_data['id']
        seen_ids.append(current_id)

        # Check if we've wrapped around to the first photo
        if current_id == first_photo_id and len(seen_ids) > 1:
            # We've successfully wrapped around
            assert len(set(seen_ids[:-1])) == 3, "Should have seen all 3 photos before wrapping"
            return

    pytest.fail("Did not wrap around after navigating through all photos")

def test_shuffle_wraparound_backward(client_for_wraparound):
    """
    Tests that plain shuffle wraps around when navigating backward from the first photo.
    """
    client, api_key = client_for_wraparound
    headers = {"Authorization": f"Client-ID {api_key}"}

    shuffle_id = 456

    # Start at the beginning
    response = client.get(f"/photos/sequence/shuffle?shuffle_id={shuffle_id}", headers=headers)
    assert response.status_code == 200
    first_photo_id = response.json()['id']

    # Navigate backward (should wrap to last photo)
    url = f"/photos/sequence/shuffle?direction=previous&current_photo_id={first_photo_id}&shuffle_id={shuffle_id}"
    response = client.get(url, headers=headers)
    assert response.status_code == 200

    last_photo_id = response.json()['id']
    assert last_photo_id != first_photo_id, "Should wrap to a different photo"

def test_new_shuffle_wraparound(client_for_wraparound):
    """
    Tests that new-shuffle wraps around correctly.
    """
    client, api_key = client_for_wraparound
    headers = {"Authorization": f"Client-ID {api_key}"}

    shuffle_id = 789

    # All 3 photos have datetime_added, so all should be in 'new' sequence
    response = client.get(f"/photos/sequence/new-shuffle?shuffle_id={shuffle_id}", headers=headers)
    assert response.status_code == 200
    first_photo_id = response.json()['id']

    # Navigate through all and verify wraparound
    current_id = first_photo_id
    seen_ids = [current_id]

    for _ in range(5):  # More than the number of photos
        url = f"/photos/sequence/new-shuffle?direction=next&current_photo_id={current_id}&shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        assert response.status_code == 200

        current_id = response.json()['id']
        seen_ids.append(current_id)

        if current_id == first_photo_id and len(seen_ids) > 1:
            # Successfully wrapped around
            return

    pytest.fail("new-shuffle did not wrap around")

def test_tagged_shuffle_wraparound(client_for_wraparound):
    """
    Tests that tagged-shuffle wraps around correctly.
    """
    client, api_key = client_for_wraparound
    headers = {"Authorization": f"Client-ID {api_key}"}

    shuffle_id = 321

    # Photos 1 and 3 are tagged
    response = client.get(f"/photos/sequence/tagged-shuffle?shuffle_id={shuffle_id}", headers=headers)
    assert response.status_code == 200
    first_photo_id = response.json()['id']
    assert first_photo_id in [1, 3], "Should start with a tagged photo"

    # Navigate forward
    url = f"/photos/sequence/tagged-shuffle?direction=next&current_photo_id={first_photo_id}&shuffle_id={shuffle_id}"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    second_photo_id = response.json()['id']
    assert second_photo_id in [1, 3], "Should only show tagged photos"

    # Navigate forward again (should wrap around)
    url = f"/photos/sequence/tagged-shuffle?direction=next&current_photo_id={second_photo_id}&shuffle_id={shuffle_id}"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    third_photo_id = response.json()['id']
    assert third_photo_id in [1, 3], "Should wrap to a tagged photo"

def test_untagged_shuffle_wraparound(client_for_wraparound):
    """
    Tests that untagged-shuffle wraps around correctly.
    """
    client, api_key = client_for_wraparound
    headers = {"Authorization": f"Client-ID {api_key}"}

    shuffle_id = 654

    # Only photo 2 is untagged
    response = client.get(f"/photos/sequence/untagged-shuffle?shuffle_id={shuffle_id}", headers=headers)
    assert response.status_code == 200
    photo_id = response.json()['id']
    assert photo_id == 2, "Should be the only untagged photo"

    # Navigate forward (should wrap back to the same photo since there's only one)
    url = f"/photos/sequence/untagged-shuffle?direction=next&current_photo_id={photo_id}&shuffle_id={shuffle_id}"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    next_photo_id = response.json()['id']
    assert next_photo_id == 2, "Should wrap back to the same untagged photo"

def test_new_sequence_wraparound(client_for_wraparound):
    """
    Tests that regular 'new' sequence (non-shuffle) wraps around correctly.
    """
    client, api_key = client_for_wraparound
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Get the newest photo (should be photo 3)
    response = client.get("/photos/sequence/new", headers=headers)
    assert response.status_code == 200
    # Could be any of the 3 since it picks randomly from top 1000

    # Let's manually find the last photo in sequence (oldest with datetime_added)
    # In our data, photo 1 has the oldest datetime_added
    last_photo_id = 1

    # Navigate forward from the last photo
    url = f"/photos/sequence/new?direction=next&current_photo_id={last_photo_id}"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    wrapped_photo_id = response.json()['id']
    assert wrapped_photo_id != last_photo_id, "Should wrap to a different photo"
    assert wrapped_photo_id in [1, 2, 3], "Should wrap to a photo in the new sequence"

def test_tagged_sequence_wraparound(client_for_wraparound):
    """
    Tests that regular 'tagged' sequence wraps around.
    """
    client, api_key = client_for_wraparound
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Tagged photos are 1 and 3, ordered by ID ASC, so first=1, last=3

    # Navigate forward from last tagged photo (3)
    url = "/photos/sequence/tagged?direction=next&current_photo_id=3"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    wrapped_photo_id = response.json()['id']
    assert wrapped_photo_id == 1, f"Should wrap to first tagged photo (1), got {wrapped_photo_id}"

def test_untagged_sequence_wraparound(client_for_wraparound):
    """
    Tests that regular 'untagged' sequence wraps around.
    """
    client, api_key = client_for_wraparound
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Only photo 2 is untagged
    # Navigate forward from photo 2
    url = "/photos/sequence/untagged?direction=next&current_photo_id=2"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    wrapped_photo_id = response.json()['id']
    assert wrapped_photo_id == 2, "Should wrap back to the only untagged photo"
