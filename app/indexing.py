import os
import logging
import time
from pathlib import Path
from . import database
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime

def _convert_gps_to_decimal(dms, ref):
    """Converts GPS coordinates from DMS (degrees, minutes, seconds) to decimal."""
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    decimal = degrees + minutes + seconds
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

def _get_exif_data(image_path):
    """Extracts width, height, geolocation, and datetime_taken from image EXIF data."""
    try:
        image = Image.open(image_path)
        width, height = image.size
        exif_data = image._getexif()
        
        geolocation = None
        datetime_taken = None

        if exif_data:
            exif = {
                TAGS[k]: v
                for k, v in exif_data.items()
                if k in TAGS
            }
            
            # Extract datetime taken
            dt_str = exif.get('DateTimeOriginal')
            if dt_str:
                try:
                    # Convert 'YYYY:MM:DD HH:MM:SS' to ISO 8601 format
                    dt_obj = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                    datetime_taken = dt_obj.isoformat()
                except (ValueError, TypeError):
                    pass

            # Extract geolocation
            gps_info = exif.get('GPSInfo')
            if gps_info:
                lat_dms = gps_info.get(2)
                lat_ref = gps_info.get(1)
                lon_dms = gps_info.get(4)
                lon_ref = gps_info.get(3)

                if lat_dms and lat_ref and lon_dms and lon_ref:
                    lat = _convert_gps_to_decimal(lat_dms, lat_ref)
                    lon = _convert_gps_to_decimal(lon_dms, lon_ref)
                    geolocation = f"{lat},{lon}"

        return width, height, geolocation, datetime_taken
    except Exception as e:
        logging.warning(f"Could not process EXIF data for {image_path}: {e}")
        # Try to get width/height even if EXIF fails
        try:
            image = Image.open(image_path)
            return image.size[0], image.size[1], None, None
        except Exception as e2:
            logging.error(f"Could not even open image {image_path}: {e2}")
            return None, None, None, None


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
                    
                    width, height, geolocation, datetime_taken = _get_exif_data(f)
                    if width is not None:
                        database.add_photo_to_index(str(f), width, height, geolocation, datetime_taken)
                        photos_discovered += 1

                    if photos_discovered % 100 == 0 and photos_discovered > 0:
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
            f"Indexing finished. Discovered {photos_discovered} photos in {total_time:.2f}s. "
            f"Average rate: {avg_rate:.2f} photos/sec"
        )
    else:
        logging.info(f"Indexing finished. Discovered {photos_discovered} photos.")