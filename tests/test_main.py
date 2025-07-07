import os
import sys
import pytest
import time
import sqlite3
from fastapi.testclient import TestClient
import importlib

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the modules that will need reloading
from app import main, database

@pytest.fixture(scope="session")
def sample_photos_path():
    """Returns the absolute path to the sample_photos directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sample_photos'))

@pytest.fixture(scope="function")
def test_client(monkeypatch, sample_photos_path, tmp_path):
    """
    Creates a TestClient with a patched environment for each test function.
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("PHOTOSHARE_DATABASE_FILE", str(db_path))
    monkeypatch.setenv("PHOTOSHARE_API_KEY", "test_key")
    monkeypatch.setenv("PHOTOSHARE_PHOTO_DIRS", sample_photos_path)
    monkeypatch.setenv("PHOTOSHARE_PHOTO_IGNORE_PATS", "")

    # Reload the modules to ensure the patched environment is used
    importlib.reload(database)
    importlib.reload(main)
    
    with TestClient(main.app) as client:
        # Wait for the background thread to initialize and index the photos
        timeout = 10
        start_time = time.time()
        conn = sqlite3.connect(db_path, timeout=timeout)
        while time.time() - start_time < timeout:
            try:
                count = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
                if count > 0:
                    break
            except sqlite3.OperationalError:
                time.sleep(0.1)
        else:
            pytest.fail("Timeout waiting for photo index to populate.")
        conn.close()
        yield client

def test_get_random_photo_success(test_client):
    """
    Tests successful retrieval of a random photo's JSON details.
    """
    headers = {"Authorization": "Client-ID test_key"}
    response = test_client.get("/photos/random", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data

def test_get_random_photo_no_api_key_header(test_client):
    """
    Tests that a 401 is returned when the Authorization header is missing.
    """
    response = test_client.get("/photos/random")
    assert response.status_code == 401

def test_get_random_photo_wrong_api_key(test_client):
    """
    Tests that a 401 is returned for an invalid API key.
    """
    headers = {"Authorization": "Client-ID wrong_key"}
    response = test_client.get("/photos/random", headers=headers)
    assert response.status_code == 401