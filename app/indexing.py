import os
import logging
import time
from pathlib import Path
from . import database

def run_indexing():
    """
    Scans photo directories, respects ignore patterns, and logs progress
    while adding photos to the database.
    """
    logging.info("Photo indexing process started.")
    
    # Load ignore patterns
    ignore_pats = []
    ignore_file = os.environ.get("PHOTOSHARE_PHOTO_IGNORE_PATS")
    if ignore_file and os.path.exists(ignore_file):
        try:
            with open(ignore_file, 'r') as f:
                ignore_pats = [line.strip() for line in f if line.strip()]
            logging.info(f"Loaded {len(ignore_pats)} ignore patterns from {ignore_file}.")
        except Exception as e:
            logging.error(f"Could not read ignore file {ignore_file}: {e}")

    # Discover and index photos
    photo_dirs_str = os.environ.get("PHOTOSHARE_PHOTO_DIRS", "")
    photo_dirs = photo_dirs_str.split(',') if photo_dirs_str else []

    if not photo_dirs:
        logging.warning("PHOTOSHARE_PHOTO_DIRS is not set. No photos will be served.")
        return

    photos_discovered = 0
    start_time = time.time()

    for photo_dir in photo_dirs:
        p = Path(photo_dir)
        if p.is_dir():
            for f in p.glob('**/*'):
                if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    if any(f.match(pat) for pat in ignore_pats):
                        logging.info(f"Ignoring photo due to match: {f}")
                        continue
                    
                    database.add_photo_to_index(str(f))
                    photos_discovered += 1

                    if photos_discovered % 100 == 0:
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 0:
                            photos_per_second = photos_discovered / elapsed_time
                            logging.info(
                                f"Discovered {photos_discovered} photos. "
                                f"Rate: {photos_per_second:.2f} photos/sec"
                            )

    total_time = time.time() - start_time
    if total_time > 0:
        avg_rate = photos_discovered / total_time
        logging.info(
            f"Indexing finished. Discovered {photos_discovered} new photos in {total_time:.2f}s. "
            f"Average rate: {avg_rate:.2f} photos/sec"
        )
    else:
        logging.info(f"Indexing finished. Discovered {photos_discovered} new photos.")
