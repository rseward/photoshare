import pytest
import sqlite3
import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.zipdownload import ZipDownloader

@pytest.fixture
def downloader():
    return ZipDownloader()

def create_dummy_files(tmp_path, filenames):
    """Create dummy files in a temporary directory."""
    for name in filenames:
        file_path = tmp_path / name
        file_path.touch()
    return [str(tmp_path / name) for name in filenames]

@pytest.mark.asyncio
@patch('app.database.get_db_connection')
async def test_create_zip_for_tag_success(mock_get_db_connection, downloader, tmp_path):
    """Test successful creation of a zip file for a given tag."""
    # Arrange
    dummy_files = create_dummy_files(tmp_path, ["photo1.jpg", "photo2.png"])
    mock_conn = MagicMock()
    mock_conn.execute().fetchall.return_value = [{'path': p} for p in dummy_files]
    mock_get_db_connection.return_value = mock_conn
    
    # Act
    response = downloader.create_zip_for_tag("test_tag")
    
    # Assert
    assert response.media_type == "application/x-zip-compressed"
    assert "attachment; filename=" in response.headers['Content-Disposition']
    
    # Verify zip content
    zip_content = b""
    async for chunk in response.body_iterator:
        zip_content += chunk
    zip_io = BytesIO(zip_content)
    
    with zipfile.ZipFile(zip_io, 'r') as zipf:
        assert len(zipf.namelist()) == 2
        assert "photo1.jpg" in zipf.namelist()
        assert "photo2.png" in zipf.namelist()

@patch('app.database.get_db_connection')
def test_create_zip_for_tag_no_photos(mock_get_db_connection, downloader):
    """Test the case where no photos are found for a tag."""
    # Arrange
    mock_conn = MagicMock()
    mock_conn.execute().fetchall.return_value = []
    mock_get_db_connection.return_value = mock_conn
    
    # Act & Assert
    with pytest.raises(HTTPException) as excinfo:
        downloader.create_zip_for_tag("empty_tag")
    assert excinfo.value.status_code == 404

@patch('app.database.get_db_connection')
def test_create_zip_for_tag_db_error(mock_get_db_connection, downloader):
    """Test handling of a database error."""
    # Arrange
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = sqlite3.Error("Test DB Error")
    mock_get_db_connection.return_value = mock_conn
    
    # Act & Assert
    with pytest.raises(HTTPException) as excinfo:
        downloader.create_zip_for_tag("error_tag")
    assert excinfo.value.status_code == 500

@pytest.mark.asyncio
@patch('app.database.get_db_connection')
async def test_create_zip_for_tag_filename_conflict(mock_get_db_connection, downloader, tmp_path):
    """Test handling of filename conflicts when creating the zip."""
    # Arrange
    p1 = tmp_path / "folder1"
    p1.mkdir()
    p2 = tmp_path / "folder2"
    p2.mkdir()
    
    dummy_files = [
        str(p1 / "photo.jpg"),
        str(p2 / "photo.jpg")
    ]
    (p1 / "photo.jpg").touch()
    (p2 / "photo.jpg").touch()

    mock_conn = MagicMock()
    mock_conn.execute().fetchall.return_value = [{'path': p} for p in dummy_files]
    mock_get_db_connection.return_value = mock_conn
    
    # Act
    response = downloader.create_zip_for_tag("conflict_tag")
    
    # Assert
    zip_content = b""
    async for chunk in response.body_iterator:
        zip_content += chunk
    zip_io = BytesIO(zip_content)
    
    with zipfile.ZipFile(zip_io, 'r') as zipf:
        assert len(zipf.namelist()) == 2
        # Check that one of the filenames is the original and the other is a UUID-prefixed version
        original_found = "photo.jpg" in zipf.namelist()
        uuid_found = any(name.endswith(".jpg") and name != "photo.jpg" for name in zipf.namelist())
        assert original_found
        assert uuid_found
