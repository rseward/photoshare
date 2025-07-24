import pytest
from fastapi.testclient import TestClient
import os
import sqlite3
from app.main import app
from app.database import init_db

TEST_DB = "test_untagged_photo_sequence.db"
TEST_API_KEY = "test-key"

@pytest.fixture
def client():
    os.environ["PHOTOSHARE_API_KEY"] = TEST_API_KEY
    os.environ["PHOTOSHARE_DATABASE_FILE"] = TEST_DB

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    # The init_db function creates its own connection using the env var
    init_db()

    # We need a separate connection to insert test data
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    for i in range(20):
        cursor.execute(
            "INSERT INTO photos (path, width, height) VALUES (?, ?, ?)",
            (f"/fake/path/photo_{i}.jpg", 800, 600)
        )
    # Add one tagged photo to make sure it's ignored
    cursor.execute(
        "INSERT INTO photos (path, width, height, tags) VALUES (?, ?, ?, ?)",
        ("/fake/path/tagged_photo.jpg", 800, 600, "tagged")
    )
    conn.commit()
    conn.close()

    with TestClient(app) as c:
        yield c

    # Teardown
    os.remove(TEST_DB)
    del os.environ["PHOTOSHARE_API_KEY"]
    del os.environ["PHOTOSHARE_DATABASE_FILE"]


def test_get_untagged_photos_returns_correct_number_of_unique_photos(client):
    """
    Tests that the /photos/untagged endpoint returns a list of unique photos
    with the specified limit.
    """
    headers = {"Authorization": f"Client-ID {TEST_API_KEY}"}
    response = client.get("/photos/untagged?limit=15", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "photos" in data
    photos = data["photos"]
    assert isinstance(photos, list)
    
    assert len(photos) == 15, f"Expected 15 photos, but got {len(photos)}."

    photo_ids = [p["id"] for p in photos]
    assert len(photo_ids) == len(set(photo_ids)), "Returned photo IDs are not unique."

def test_untagged_sequence_wraparound_from_last_photo(client):
    """
    Tests that navigating 'next' from the last untagged photo wraps around to the first one.
    """
    # Connect to the test DB to find the first and last untagged photo IDs
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM photos WHERE tags IS NULL OR tags = '' ORDER BY id ASC LIMIT 1")
    first_photo_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM photos WHERE tags IS NULL OR tags = '' ORDER BY id DESC LIMIT 1")
    last_photo_id = cursor.fetchone()[0]
    conn.close()

    headers = {"Authorization": f"Client-ID {TEST_API_KEY}"}
    # Request the next photo from the last one
    response = client.get(f"/photos/sequence/untagged?current_photo_id={last_photo_id}&direction=next", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # The bug is that it returns the same photo instead of wrapping around
    assert data['id'] != last_photo_id, "The sequence should not return the same photo."
    assert data['id'] == first_photo_id, f"Expected to wrap around to photo {first_photo_id}, but got {data['id']}."
