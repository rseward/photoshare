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
    """Initializes the database and handles schema migrations."""
    logging.info(f"Initializing database at {get_db_path()}")
    conn = get_db_connection()
    try:
        # Create table if it doesn't exist
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

        # Check for and add missing columns (simple migration)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(photos)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'datetime_added' not in columns:
            logging.info("Adding 'datetime_added' column to photos table.")
            conn.execute("ALTER TABLE photos ADD COLUMN datetime_added TEXT;")

        if 'md5sum' not in columns:
            logging.info("Adding 'md5sum' column to photos table.")
            conn.execute("ALTER TABLE photos ADD COLUMN md5sum TEXT;")

        conn.commit()

        # Back-fill missing datetime_added values
        cursor.execute("SELECT id, path FROM photos WHERE datetime_added IS NULL")
        missing_datetime_rows = cursor.fetchall()
        if missing_datetime_rows:
            logging.info(f"Found {len(missing_datetime_rows)} photos with missing datetime_added. Back-filling...")
            for row in missing_datetime_rows:
                try:
                    if os.path.exists(row['path']):
                        mtime = os.path.getmtime(row['path'])
                        dt_object = datetime.fromtimestamp(mtime, timezone.utc)
                        iso_date = dt_object.isoformat()
                        conn.execute("UPDATE photos SET datetime_added = ? WHERE id = ?", (iso_date, row['id']))
                    else:
                        logging.warning(f"Photo path not found, cannot back-fill datetime_added for ID {row['id']}: {row['path']}")
                except Exception as e:
                    logging.warning(f"Could not back-fill datetime_added for photo ID {row['id']}: {e}")
            conn.commit()
            logging.info("Finished back-filling datetime_added.")

    except sqlite3.Error as e:
        logging.error(f"Database initialization failed: {e}")
    finally:
        conn.close()

def add_photo_to_index(photo_path: str, md5sum: str, exif_data: dict | None, update_md5sum: bool = False):
    """Adds or updates a photo in the database index."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, md5sum FROM photos WHERE path = ?", (str(photo_path),))
        row = cursor.fetchone()
        
        if row:
            # Existing photo: build a dynamic update statement
            update_clauses = []
            update_params = []
            
            if exif_data:
                update_clauses.extend(["width = ?", "height = ?", "geolocation = ?", "datetime_taken = ?"])
                update_params.extend([exif_data['width'], exif_data['height'], exif_data['geolocation'], exif_data['datetime_taken']])
            
            if update_md5sum and row['md5sum'] != md5sum:
                update_clauses.append("md5sum = ?")
                update_params.append(md5sum)
            
            if update_clauses:
                query = "UPDATE photos SET " + ", ".join(update_clauses) + " WHERE id = ?"
                update_params.append(row['id'])
                cursor.execute(query, tuple(update_params))
                logging.info(f"Updated photo metadata for: {photo_path}")

        else:
            # New photo: must have EXIF data
            if not exif_data:
                logging.warning(f"Skipping new photo because EXIF data was missing: {photo_path}")
                return

            datetime_added = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO photos (path, width, height, geolocation, datetime_taken, datetime_added, md5sum) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(photo_path), exif_data['width'], exif_data['height'], exif_data['geolocation'], exif_data['datetime_taken'], datetime_added, md5sum)
            )
            logging.info(f"Indexed new photo: {photo_path}")
        
        conn.commit()

    except sqlite3.IntegrityError:
        logging.warning(f"Integrity error for photo {photo_path}, likely a race condition. Skipping.")
    except Exception as e:
        logging.error(f"Failed to index photo {photo_path}: {e}")
    finally:
        conn.close()

def get_all_tags(sort_by: str = 'tag', order: str = 'asc', search: str = ''):
    """Gets all tags with their counts, with sorting and searching."""
    conn = get_db_connection()
    try:
        # Base query to get tags and their counts
        query = "SELECT tags FROM photos WHERE tags IS NOT NULL AND tags != ''"
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        tag_counts = {}
        for row in rows:
            tags = row['tags'].split(',')
            for tag in tags:
                tag = tag.strip()
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Search
        if search:
            tag_counts = {tag: count for tag, count in tag_counts.items() if search.lower() in tag.lower()}

        # Sort
        if sort_by == 'tag':
            sorted_tags = sorted(tag_counts.items(), key=lambda item: item[0], reverse=order == 'desc')
        elif sort_by == 'count':
            sorted_tags = sorted(tag_counts.items(), key=lambda item: item[1], reverse=order == 'desc')
        else:
            sorted_tags = sorted(tag_counts.items())

        return [{"tag": tag, "count": count} for tag, count in sorted_tags]

    except sqlite3.Error as e:
        logging.error(f"Database error when getting all tags: {e}")
        return []
    finally:
        conn.close()