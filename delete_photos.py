#!/usr/bin/env python

import cv2
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import shutil

def get_db_path():
    """Gets the database file path from the environment variable."""
    return os.environ.get("PHOTOSHARE_DATABASE_FILE", "photoshare.db")

def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def get_photo_details(photo_path):
    """Gets tags and EXIF data for a photo."""
    conn = get_db_connection()
    try:
        photo = conn.execute("SELECT tags, datetime_taken, geolocation FROM photos WHERE path = ?", (photo_path,)).fetchone()
        return photo
    except sqlite3.Error as e:
        print(f"Database error when fetching photo details: {e}")
        return None
    finally:
        conn.close()

def main():
    """Main function to review and delete photos."""
    db_dir = Path(get_db_path()).parent
    delete_file = db_dir / "photos_to_delete.txt"

    if not delete_file.exists():
        print("No photos to delete.")
        return

    with open(delete_file, "r") as f:
        photos_to_delete = [line.strip() for line in f if line.strip()]

    remaining_photos = []
    total_photos = len(photos_to_delete)

    for i, photo_path in enumerate(photos_to_delete):
        if not os.path.exists(photo_path):
            print(f"Photo not found: {photo_path}")
            continue

        img = cv2.imread(photo_path)
        if img is None:
            print(f"Could not read image: {photo_path}")
            continue

        details = get_photo_details(photo_path)
        tags = details['tags'] if details and details['tags'] else "No tags"
        exif_info = ""
        if details and details['datetime_taken']:
            exif_info += f"Taken: {details['datetime_taken']} "
        if details and details['geolocation']:
            exif_info += f"Location: {details['geolocation']}"

        # Display photo and info
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_color = (0, 255, 0)
        line_type = 2

        # Add text overlays
        cv2.putText(img, tags, (10, 30), font, font_scale, font_color, line_type)
        cv2.putText(img, exif_info, (10, 60), font, font_scale, font_color, line_type)
        status_text = f"Press d to delete or s to skip. {i + 1} / {total_photos} photos reviewed"
        cv2.putText(img, status_text, (10, img.shape[0] - 10), font, font_scale, font_color, line_type)

        cv2.imshow("Delete Reviewer", img)
        key = cv2.waitKey(0)

        if key == ord('d'):
            try:
                shutil.move(photo_path, "/tmp/")
                print(f"Moved {photo_path} to /tmp/")

                # Update database
                conn = get_db_connection()
                try:
                    iso_date = datetime.now(timezone.utc).isoformat()
                    conn.execute("UPDATE photos SET datetime_deleted = ? WHERE path = ?", (iso_date, photo_path))
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"Database error when updating datetime_deleted: {e}")
                finally:
                    conn.close()

            except Exception as e:
                print(f"Error moving file: {e}")
                remaining_photos.append(photo_path)

        elif key == ord('s'):
            remaining_photos.append(photo_path)
        else:
            remaining_photos.append(photo_path)

        cv2.destroyAllWindows()

    with open(delete_file, "w") as f:
        for photo in remaining_photos:
            f.write(f"{photo}\n")

    print("Review complete.")

if __name__ == "__main__":
    main()
