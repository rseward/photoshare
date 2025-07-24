#!/usr/bin/env python

import click
import os
import logging
import hashlib
from pathlib import Path
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up imports for the application modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
from app import database

# Configure logging to print to console
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

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
    Scans a directory for photos, and creates relative symbolic links in 'new'
    or 'existing' subdirectories based on whether the photo's MD5 sum is in the database.
    """
    photos_path = Path(photos_path)
    new_dir = photos_path / 'new'
    existing_dir = photos_path / 'existing'

    new_dir.mkdir(exist_ok=True)
    existing_dir.mkdir(exist_ok=True)

    logging.info("Initializing database and fetching existing MD5 sums...")
    database.init_db()
    conn = database.get_db_connection()
    try:
        # This set will act as our dictionary of all known MD5s.
        known_md5sum_set = {row['md5sum'] for row in conn.execute("SELECT md5sum FROM photos WHERE md5sum IS NOT NULL")}
    finally:
        conn.close()
    logging.info(f"Found {len(known_md5sum_set)} existing photos in the database.")

    new_linked_count = 0
    existing_linked_count = 0
    processed_count = 0
    discovered_count = 0
    collision_warnings = 0
    
    start_time = time.time()
    last_log_time = start_time

    common_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
    
    logging.info("Starting photo discovery and processing...")
    
    all_files = photos_path.glob('**/*')

    for f in all_files:
        if f.is_dir() or f.parent.name in ['new', 'existing']:
            continue

        if f.suffix.lower() in common_extensions:
            discovered_count += 1
            
            md5sum = _calculate_md5sum(f)
            if not md5sum:
                logging.warning(f"Could not calculate md5sum for {f}, skipping.")
                continue
            
            processed_count += 1

            # If md5sum is in our set, it's existing. Otherwise, it's new.
            if md5sum in known_md5sum_set:
                target_dir = existing_dir
            else:
                target_dir = new_dir

            link_path = target_dir / f.name
            if link_path.exists():
                if not link_path.samefile(f):
                    logging.warning(f"Filename collision: link '{link_path.name}' already exists. Skipping.")
                    collision_warnings += 1
                continue

            try:
                relative_path = os.path.relpath(f, target_dir)
                os.symlink(relative_path, link_path)
                
                if target_dir == new_dir:
                    new_linked_count += 1
                    # Add the new md5 to the set to handle duplicates during this run.
                    known_md5sum_set.add(md5sum)
                else:
                    existing_linked_count += 1
                    
            except Exception as e:
                logging.error(f"Failed to create symlink for {f}: {e}")

            # Progress reporting
            current_time = time.time()
            if current_time - last_log_time > 15:
                elapsed_time = current_time - start_time
                discovery_rate = discovered_count / elapsed_time if elapsed_time > 0 else 0
                processing_rate = processed_count / elapsed_time if elapsed_time > 0 else 0
                logging.info(
                    f"Progress: {processed_count} files processed. "
                    f"New Links: {new_linked_count}, Existing Links: {existing_linked_count}. "
                    f"Discovery: {discovery_rate:.2f} files/s, "
                    f"Processing: {processing_rate:.2f} files/s."
                )
                last_log_time = current_time

    # Final summary
    total_time = time.time() - start_time
    discovery_rate = discovered_count / total_time if total_time > 0 else 0
    processing_rate = processed_count / total_time if total_time > 0 else 0
    logging.info("--------------------")
    logging.info("Import complete.")
    logging.info(f"Total time: {total_time:.2f}s")
    logging.info(f"Files discovered: {discovered_count} ({discovery_rate:.2f} files/s)")
    logging.info(f"Files processed: {processed_count} ({processing_rate:.2f} files/s)")
    logging.info(f"New photos linked: {new_linked_count}")
    logging.info(f"Existing photos linked: {existing_linked_count}")
    if collision_warnings > 0:
        logging.warning(f"Filename collisions prevented linking {collision_warnings} files.")
    logging.info("--------------------")


if __name__ == '__main__':
    import_photos()