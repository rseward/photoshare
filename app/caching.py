import logging
import sqlite3
import threading
from threading import Lock
from . import database

log = logging.getLogger(__name__)

# In-memory cache for tag counts
_tag_counts_cache = {}
_cache_lock = Lock()

def get_tag_counts():
    """Returns a copy of the tag counts from the cache."""
    with _cache_lock:
        return _tag_counts_cache.copy()

def _calculate_tag_counts():
    """Calculates tag counts from the database."""
    log.info("Calculating tag counts from database...")
    conn = database.get_db_connection()
    tag_counts = {}
    try:
        photos = conn.execute("SELECT tags FROM photos WHERE tags IS NOT NULL AND tags != ''").fetchall()
        for photo in photos:
            if photo['tags']:
                for tag in photo['tags'].split(','):
                    tag = tag.strip()
                    if tag:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
        log.info(f"Calculated {len(tag_counts)} unique tags.")
        return tag_counts
    except sqlite3.Error as e:
        log.error(f"Database error when calculating tag counts: {e}")
        return {}
    finally:
        conn.close()

def update_tag_counts_cache():
    """Updates the tag counts cache with fresh data from the database."""
    log.info("Updating tag counts cache...")
    new_counts = _calculate_tag_counts()
    with _cache_lock:
        global _tag_counts_cache
        _tag_counts_cache = new_counts
    log.info("Tag counts cache updated.")

def start_background_refresh():
    """Starts a background timer to refresh the tag counts cache every 5 minutes."""
    log.info("Starting background cache refresh timer.")
    # Initial population
    update_tag_counts_cache()
    
    # Schedule periodic updates
    timer = threading.Timer(300, _background_refresh_task)
    timer.daemon = True
    timer.start()

def _background_refresh_task():
    """The task that runs periodically to refresh the cache."""
    update_tag_counts_cache()
    # Reschedule the timer
    timer = threading.Timer(300, _background_refresh_task)
    timer.daemon = True
    timer.start()
