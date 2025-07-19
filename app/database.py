import sqlite3
import logging
import os
import cv2

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
                tags TEXT
            );
        """)
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database initialization failed: {e}")
    finally:
        conn.close()

def add_photo_to_index(photo_path: str):
    """Adds a photo to the database index. Skips if it already exists."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM photos WHERE path = ?", (str(photo_path),))
        if cursor.fetchone():
            return

        img = cv2.imread(str(photo_path))
        if img is None:
            logging.warning(f"Could not read image file, skipping: {photo_path}")
            return
        
        height, width, _ = img.shape
        conn.execute(
            "INSERT INTO photos (path, width, height) VALUES (?, ?, ?)",
            (str(photo_path), width, height)
        )
        conn.commit()
        logging.info(f"Indexed photo: {photo_path}")

    except sqlite3.IntegrityError:
        pass
    except Exception as e:
        logging.error(f"Failed to index photo {photo_path}: {e}")
    finally:
        conn.close()