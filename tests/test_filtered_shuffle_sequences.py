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
def client_for_filtered_shuffle(monkeypatch, tmp_path):
    """
    Creates a TestClient with a pre-populated database
    for testing filtered shuffle sequences (new-shuffle, tagged-shuffle, untagged-shuffle).
    """
    db_path = tmp_path / "test_filtered_shuffle.db"
    api_key = "test_key_filtered_shuffle"

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

    # Insert test data with varied tagging and datetime_added
    now = datetime.now(timezone.utc)
    photo_data = [
        # ID, path, width, height, datetime_added, tags
        (1, "/fake/path1.jpg", 100, 100, (now - timedelta(days=5)).isoformat(), "vacation"),
        (2, "/fake/path2.jpg", 100, 100, (now - timedelta(days=4)).isoformat(), "family"),
        (3, "/fake/path3.jpg", 100, 100, (now - timedelta(days=3)).isoformat(), None),  # untagged
        (4, "/fake/path4.jpg", 100, 100, (now - timedelta(days=2)).isoformat(), "landscape"),
        (5, "/fake/path5.jpg", 100, 100, (now - timedelta(days=1)).isoformat(), None),  # untagged
        (6, "/fake/path6.jpg", 100, 100, now.isoformat(), "portrait"),
        (7, "/fake/path7.jpg", 100, 100, None, "test"),  # No datetime_added (old photo)
        (8, "/fake/path8.jpg", 100, 100, None, None),  # No datetime_added, untagged
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

def test_new_shuffle_returns_shuffle_id(client_for_filtered_shuffle):
    """
    Tests that the new-shuffle endpoint returns a shuffle_id.
    """
    client, api_key = client_for_filtered_shuffle
    headers = {"Authorization": f"Client-ID {api_key}"}

    response = client.get("/photos/sequence/new-shuffle", headers=headers)
    assert response.status_code == 200, f"Request failed: {response.text}"

    photo_data = response.json()
    assert 'shuffle_id' in photo_data, "shuffle_id not found in response"
    assert isinstance(photo_data['shuffle_id'], int), "shuffle_id should be an integer"
    assert 100 <= photo_data['shuffle_id'] <= 10000, "shuffle_id should be between 100 and 10000"

    # Verify the photo has datetime_added (is from the 'new' set)
    # Photos with datetime_added: 1, 2, 3, 4, 5, 6
    assert photo_data['id'] in [1, 2, 3, 4, 5, 6], "Photo should be from the 'new' set"

def test_tagged_shuffle_navigation(client_for_filtered_shuffle):
    """
    Tests that navigation with tagged-shuffle works correctly.
    """
    client, api_key = client_for_filtered_shuffle
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Fetch the first photo
    response = client.get("/photos/sequence/tagged-shuffle", headers=headers)
    assert response.status_code == 200

    photo_data = response.json()
    shuffle_id = photo_data['shuffle_id']
    first_photo_id = photo_data['id']

    # Verify photo is tagged (has tags)
    # Tagged photos: 1, 2, 4, 6, 7
    assert first_photo_id in [1, 2, 4, 6, 7], "Photo should be tagged"

    # Navigate forward
    photo_ids = [first_photo_id]
    current_id = first_photo_id

    for _ in range(3):  # Navigate through 3 more photos
        url = f"/photos/sequence/tagged-shuffle?direction=next&current_photo_id={current_id}&shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        assert response.status_code == 200

        photo_data = response.json()
        assert photo_data['id'] in [1, 2, 4, 6, 7], "All photos should be tagged"
        photo_ids.append(photo_data['id'])
        current_id = photo_data['id']

    # Navigate backward
    for _ in range(3):
        url = f"/photos/sequence/tagged-shuffle?direction=previous&current_photo_id={current_id}&shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        assert response.status_code == 200

        photo_data = response.json()
        current_id = photo_data['id']

    # Should be back near the start
    assert current_id == first_photo_id, "Should navigate back to first photo"

def test_untagged_shuffle_filters_correctly(client_for_filtered_shuffle):
    """
    Tests that untagged-shuffle only returns untagged photos.
    """
    client, api_key = client_for_filtered_shuffle
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Expected untagged photos: 3, 5, 8
    untagged_ids = {3, 5, 8}
    seen_ids = set()

    # Fetch initial photo
    response = client.get("/photos/sequence/untagged-shuffle", headers=headers)
    assert response.status_code == 200

    photo_data = response.json()
    shuffle_id = photo_data['shuffle_id']
    current_id = photo_data['id']

    assert current_id in untagged_ids, f"Photo {current_id} should be untagged"
    seen_ids.add(current_id)

    # Navigate through all untagged photos
    for _ in range(5):  # Try to see all 3 untagged photos
        url = f"/photos/sequence/untagged-shuffle?direction=next&current_photo_id={current_id}&shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        assert response.status_code == 200

        photo_data = response.json()
        current_id = photo_data['id']
        assert current_id in untagged_ids, f"Photo {current_id} should be untagged"
        seen_ids.add(current_id)

        # Stop if we've wrapped around
        if len(seen_ids) == len(untagged_ids) and current_id == list(seen_ids)[0]:
            break

def test_new_shuffle_consistency(client_for_filtered_shuffle):
    """
    Tests that new-shuffle with same shuffle_id produces consistent order.
    """
    client, api_key = client_for_filtered_shuffle
    headers = {"Authorization": f"Client-ID {api_key}"}

    shuffle_id = 5678

    def get_sequence(count=4):
        url = f"/photos/sequence/new-shuffle?shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        photo_data = response.json()

        sequence = [photo_data['id']]
        current_id = photo_data['id']

        for _ in range(count - 1):
            url = f"/photos/sequence/new-shuffle?direction=next&current_photo_id={current_id}&shuffle_id={shuffle_id}"
            response = client.get(url, headers=headers)
            photo_data = response.json()
            sequence.append(photo_data['id'])
            current_id = photo_data['id']

        return sequence

    # Get sequence twice with same shuffle_id
    sequence1 = get_sequence()
    sequence2 = get_sequence()

    # Sequences should be identical
    assert sequence1 == sequence2, \
        f"Same shuffle_id should produce identical sequences: seq1={sequence1}, seq2={sequence2}"

def test_all_shuffle_variants_exist(client_for_filtered_shuffle):
    """
    Tests that all shuffle variant endpoints exist and return valid responses.
    """
    client, api_key = client_for_filtered_shuffle
    headers = {"Authorization": f"Client-ID {api_key}"}

    shuffle_variants = ['new-shuffle', 'tagged-shuffle', 'untagged-shuffle']

    for variant in shuffle_variants:
        response = client.get(f"/photos/sequence/{variant}", headers=headers)
        assert response.status_code == 200, f"{variant} endpoint should exist"

        photo_data = response.json()
        assert 'shuffle_id' in photo_data, f"{variant} should return shuffle_id"
        assert 'id' in photo_data, f"{variant} should return photo data"
