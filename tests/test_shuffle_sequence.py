import os
import sys
import pytest
import sqlite3
from fastapi.testclient import TestClient
import importlib

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules that will need reloading
from app import main, database

@pytest.fixture
def client_for_shuffle_sequence(monkeypatch, tmp_path):
    """
    Creates a TestClient with a pre-populated database
    specifically for testing the 'shuffle' sequence.
    """
    db_path = tmp_path / "test_shuffle.db"
    api_key = "test_key_shuffle"

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

    # Insert test data with 10 photos
    photo_data = [
        (i, f"/fake/path{i}.jpg", 100, 100) for i in range(1, 11)
    ]

    conn.executemany(
        "INSERT INTO photos (id, path, width, height) VALUES (?, ?, ?, ?)",
        photo_data
    )
    conn.commit()
    conn.close()

    # Reload modules to use the patched environment
    importlib.reload(database)
    importlib.reload(main)

    with TestClient(main.app) as client:
        yield client, api_key

def test_shuffle_returns_shuffle_id(client_for_shuffle_sequence):
    """
    Tests that the shuffle endpoint returns a shuffle_id.
    """
    client, api_key = client_for_shuffle_sequence
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Fetch the first photo
    response = client.get("/photos/sequence/shuffle", headers=headers)
    assert response.status_code == 200, f"Initial request failed: {response.text}"

    photo_data = response.json()
    assert 'shuffle_id' in photo_data, "shuffle_id not found in response"
    assert isinstance(photo_data['shuffle_id'], int), "shuffle_id should be an integer"
    assert 100 <= photo_data['shuffle_id'] <= 10000, "shuffle_id should be between 100 and 10000"

def test_shuffle_navigation_is_consistent(client_for_shuffle_sequence):
    """
    Tests that navigation with the same shuffle_id returns photos in a consistent order.
    """
    client, api_key = client_for_shuffle_sequence
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Fetch the first photo
    response = client.get("/photos/sequence/shuffle", headers=headers)
    assert response.status_code == 200, f"Initial request failed: {response.text}"

    photo_data = response.json()
    shuffle_id = photo_data['shuffle_id']
    first_photo_id = photo_data['id']

    # Navigate forward through several photos
    photo_ids_forward = [first_photo_id]
    current_photo_id = first_photo_id

    for _ in range(5):  # Navigate through 5 more photos
        url = f"/photos/sequence/shuffle?direction=next&current_photo_id={current_photo_id}&shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        assert response.status_code == 200, f"Navigation failed: {response.text}"

        photo_data = response.json()
        photo_ids_forward.append(photo_data['id'])
        current_photo_id = photo_data['id']

    # Navigate backward through the same photos
    photo_ids_backward = [current_photo_id]

    for _ in range(5):  # Navigate back through 5 photos
        url = f"/photos/sequence/shuffle?direction=previous&current_photo_id={current_photo_id}&shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        assert response.status_code == 200, f"Backward navigation failed: {response.text}"

        photo_data = response.json()
        photo_ids_backward.append(photo_data['id'])
        current_photo_id = photo_data['id']

    # Verify we got back to where we started
    photo_ids_backward.reverse()
    assert photo_ids_backward == photo_ids_forward, \
        f"Forward and backward navigation should return the same photos: forward={photo_ids_forward}, backward={photo_ids_backward}"

def test_shuffle_id_consistency(client_for_shuffle_sequence):
    """
    Tests that the same shuffle_id always produces the same photo order.
    """
    client, api_key = client_for_shuffle_sequence
    headers = {"Authorization": f"Client-ID {api_key}"}

    # Use a fixed shuffle_id for consistency
    shuffle_id = 1234

    # Navigate through several photos with the shuffle_id
    def get_sequence(shuffle_id, count=5):
        url = f"/photos/sequence/shuffle?shuffle_id={shuffle_id}"
        response = client.get(url, headers=headers)
        photo_data = response.json()

        sequence = [photo_data['id']]
        current_id = photo_data['id']

        for _ in range(count - 1):
            url = f"/photos/sequence/shuffle?direction=next&current_photo_id={current_id}&shuffle_id={shuffle_id}"
            response = client.get(url, headers=headers)
            photo_data = response.json()
            sequence.append(photo_data['id'])
            current_id = photo_data['id']

        return sequence

    # Get the sequence twice with the same shuffle_id
    sequence1 = get_sequence(shuffle_id)
    sequence2 = get_sequence(shuffle_id)

    # The sequences should be identical
    assert sequence1 == sequence2, \
        f"Same shuffle_id should always produce the same sequence: seq1={sequence1}, seq2={sequence2}"
