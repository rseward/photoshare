import pytest
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import caching
import sqlite3

@pytest.fixture(autouse=True)
def reset_cache():
    """Fixture to reset the cache before each test."""
    caching._tag_counts_cache = {}
    yield

@patch('app.database.get_db_connection')
def test_calculate_tag_counts_success(mock_get_db_connection):
    """Test that tag counts are calculated correctly from the database."""
    # Arrange
    mock_photos = [
        {'tags': 'cat,animal'},
        {'tags': 'dog,animal'},
        {'tags': 'cat,pet'},
        {'tags': '  cat  ,   spaced   '}, # Test with whitespace
        {'tags': None},
        {'tags': ''}
    ]
    mock_conn = MagicMock()
    mock_conn.execute().fetchall.return_value = mock_photos
    mock_get_db_connection.return_value = mock_conn

    # Act
    counts = caching._calculate_tag_counts()

    # Assert
    expected_counts = {'cat': 3, 'animal': 2, 'dog': 1, 'pet': 1, 'spaced': 1}
    assert counts == expected_counts

@patch('app.database.get_db_connection')
def test_calculate_tag_counts_db_error(mock_get_db_connection):
    """Test that an empty dictionary is returned on database error."""
    # Arrange
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = sqlite3.Error("DB Error")
    mock_get_db_connection.return_value = mock_conn

    # Act
    counts = caching._calculate_tag_counts()

    # Assert
    assert counts == {}

@patch('app.caching._calculate_tag_counts')
def test_update_tag_counts_cache(mock_calculate):
    """Test that the cache is updated with calculated counts."""
    # Arrange
    expected_counts = {'test': 10, 'cache': 5}
    mock_calculate.return_value = expected_counts
    
    # Act
    caching.update_tag_counts_cache()
    
    # Assert
    assert caching._tag_counts_cache == expected_counts

def test_get_tag_counts_returns_copy():
    """Test that get_tag_counts returns a copy, not a reference."""
    # Arrange
    original_cache = {'a': 1}
    with patch.dict(caching._tag_counts_cache, original_cache, clear=True):
        # Act
        retrieved_cache = caching.get_tag_counts()
        retrieved_cache['b'] = 2 # Modify the retrieved copy
        
        # Assert
        assert caching.get_tag_counts() == original_cache
        assert caching.get_tag_counts() != retrieved_cache

@patch('threading.Timer')
@patch('app.caching.update_tag_counts_cache')
def test_start_background_refresh(mock_update_cache, mock_timer):
    """Test that the background refresh starts correctly."""
    # Arrange
    mock_timer_instance = MagicMock()
    mock_timer.return_value = mock_timer_instance

    # Act
    caching.start_background_refresh()

    # Assert
    mock_update_cache.assert_called_once() # Initial update
    mock_timer.assert_called_with(300, caching._background_refresh_task)
    mock_timer_instance.start.assert_called_once()

@patch('threading.Timer')
@patch('app.caching.update_tag_counts_cache')
def test_background_refresh_task(mock_update_cache, mock_timer):
    """Test that the background refresh task updates the cache and reschedules itself."""
    # Arrange
    mock_timer_instance = MagicMock()
    mock_timer.return_value = mock_timer_instance

    # Act
    caching._background_refresh_task()

    # Assert
    mock_update_cache.assert_called_once()
    mock_timer.assert_called_with(300, caching._background_refresh_task)
    mock_timer_instance.start.assert_called_once()
