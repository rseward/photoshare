#!/usr/bin/env python

import click
import os
import logging
import hashlib
from pathlib import Path
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up imports for the application modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
from app import database

# Configure logging to print to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _calculate_md5sum(file_path):
    """Calculates the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except IOError as e:
        logging.error(f"Could not read file for md5sum: {file_path}: {e}")
        return None

@click.command()
@click.argument('photos_path', type=click.Path(exists=True, file_okay=False, resolve_path=True))
def import_photos(photos_path):
    """
    Imports photos from a specified path into the database.
    Sorts photos into 'new' and 'existing' subdirectories.
    """
    photos_path = Path(photos_path)
    new_dir = photos_path / 'new'
    existing_dir = photos_path / 'existing'

    new_dir.mkdir(exist_ok=True)
    existing_dir.mkdir(exist_ok=True)

    database.init_db()
    conn = database.get_db_connection()
    try:
        for f in photos_path.glob('**/*'):
            if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                md5sum = _calculate_md5sum(f)
                if md5sum:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM photos WHERE md5sum = ?", (md5sum,))
                    row = cursor.fetchone()

                    if row:
                        # Photo exists, move to existing
                        shutil.move(str(f), str(existing_dir / f.name))
                        logging.info(f"Photo {f.name} already exists. Moved to 'existing'.")
                    else:
                        # New photo, move to new
                        shutil.move(str(f), str(new_dir / f.name))
                        logging.info(f"New photo {f.name}. Moved to 'new'.")
    finally:
        conn.close()

if __name__ == '__main__':
    import_photos()
