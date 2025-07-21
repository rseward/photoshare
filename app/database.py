import sqlite3
import logging
import os
from datetime import datetime, timezone

def get_db_path():
    """Gets the database file path from the environment variable."""
    return os.environ.get("PHOTOSHARE_DATABASE_FILE", "photoshare.db")

def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the 'photos' table if it doesn't exist."""
    logging.info(f"Initializing database at {get_db_path()}")
    conn = get_db_connection()
    try:
        # datetime values are stored as ISO 8601 strings
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
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database initialization failed: {e}")
    finally:
        conn.close()

def add_photo_to_index(photo_path: str, width: int, height: int, geolocation: str | None, datetime_taken: str | None, md5sum: str):
    """Adds or updates a photo in the database index."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, md5sum FROM photos WHERE path = ?", (str(photo_path),))
        row = cursor.fetchone()
        
        if row:
            # Update existing photo only if md5sum has changed.
            if row['md5sum'] != md5sum:
                cursor.execute(
                    "UPDATE photos SET width = ?, height = ?, geolocation = ?, datetime_taken = ?, md5sum = ? WHERE id = ?",
                    (width, height, geolocation, datetime_taken, md5sum, row['id'])
                )
                logging.info(f"Updated photo metadata for: {photo_path}")
        else:
            # Insert new photo
            datetime_added = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO photos (path, width, height, geolocation, datetime_taken, datetime_added, md5sum) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(photo_path), width, height, geolocation, datetime_taken, datetime_added, md5sum)
            )
            logging.info(f"Indexed new photo: {photo_path}")
        
        conn.commit()

    except sqlite3.IntegrityError:
        # This can happen in a race condition if two indexers run at once.
        logging.warning(f"Integrity error for photo {photo_path}, likely a race condition. Skipping.")
        pass
    except Exception as e:
        logging.error(f"Failed to index photo {photo_path}: {e}")
    finally:
        conn.close()