import os
import sys
import logging
import time
import hashlib
from pathlib import Path
from . import database
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from functools import lru_cache
from multiprocessing import Pool, cpu_count
from dotenv import load_dotenv

def _format_time(seconds):
    """Formats a duration in seconds into a human-readable string like 1d2h3m4s."""
    if seconds < 0:
        return "N/A"
    
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{int(days)}d")
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    if secs > 0 or not parts:
        parts.append(f"{int(secs)}s")
        
    return "".join(parts)

def _convert_gps_to_decimal(dms, ref):
    """Converts GPS coordinates from DMS (degrees, minutes, seconds) to decimal."""
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    decimal = degrees + minutes + seconds
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

@lru_cache(maxsize=None)
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
            
            dt_str = exif.get('DateTimeOriginal')
            if dt_str:
                try:
                    dt_obj = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                    datetime_taken = dt_obj.isoformat()
                except (ValueError, TypeError):
                    pass

            gps_info = exif.get('GPSInfo')
            if gps_info:
                lat_dms, lat_ref, lon_dms, lon_ref = gps_info.get(2), gps_info.get(1), gps_info.get(4), gps_info.get(3)
                if lat_dms and lat_ref and lon_dms and lon_ref:
                    lat = _convert_gps_to_decimal(lat_dms, lat_ref)
                    lon = _convert_gps_to_decimal(lon_dms, lon_ref)
                    geolocation = f"{lat},{lon}"

        return {'width': width, 'height': height, 'geolocation': geolocation, 'datetime_taken': datetime_taken}
    except Exception as e:
        logging.warning(f"Could not process EXIF data for {image_path}: {e}")
        try:
            image = Image.open(image_path)
            return {'width': image.size[0], 'height': image.size[1], 'geolocation': None, 'datetime_taken': None}
        except Exception as e2:
            logging.error(f"Could not even open image {image_path}: {e2}")
            return None

def _process_photo_wrapper(args):
    """Helper to unpack arguments for the worker."""
    return _process_photo(*args)

def _process_photo(photo_path, needs_exif):
    """Worker function to process a single photo and return stats."""
    exif_data = None
    exif_collected = False
    
    if needs_exif:
        exif_data = _get_exif_data(photo_path)
        if exif_data:
            if (exif_data['width'] * exif_data['height']) < 10000:
                logging.info(f"Skipping photo {photo_path} because it is too small.")
                return None
            exif_collected = True
        else:
            return None # Failed to get even basic dimensions

    md5sum = _calculate_md5sum(photo_path)
    if md5sum:
        # Return a tuple indicating success for md5 and exif collection
        return (str(photo_path), md5sum, exif_data, True, exif_collected)
    return None

def run_indexing(update_md5sum: bool = False, folder: str = None):
    """
    Scans photo directories in parallel, respects ignore patterns, and logs progress
    while adding photos to the database.
    """
    load_dotenv()
    logging.info("Photo indexing process started.")
    
    # 1. Validate configuration
    if folder:
        photo_dirs = [folder]
    else:
        photo_dirs_str = os.environ.get("PHOTOSHARE_PHOTO_DIRS", "")
        if not photo_dirs_str:
            logging.critical("CRITICAL: PHOTOSHARE_PHOTO_DIRS environment variable is not set. Terminating.")
            return
        photo_dirs = photo_dirs_str.split(',')
    
    ignore_file = os.environ.get("PHOTOSHARE_PHOTO_IGNORE_PATS")
    if ignore_file and not os.path.exists(ignore_file):
        logging.critical(f"CRITICAL: Ignore file specified but not found at '{ignore_file}'. Terminating.")
        return

    # 2. Get current state from DB
    conn = database.get_db_connection()
    try:
        photos_in_db = {row['path']: row for row in conn.execute("SELECT path, datetime_taken, metadata_extraction_attempts FROM photos")}
    finally:
        conn.close()

    # 3. Discover all photos on disk
    ignore_pats = []
    if ignore_file:
        try:
            with open(ignore_file, 'r') as f:
                ignore_pats = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logging.error(f"Could not read ignore file {ignore_file}: {e}")

    logging.info("Starting photo discovery...")
    all_photo_paths = []
    discovery_start_time = time.time()
    last_discovery_log_time = discovery_start_time
    
    for photo_dir in photo_dirs:
        p = Path(photo_dir)
        if not p.is_dir():
            logging.warning(f"Specified photo directory does not exist, skipping: {photo_dir}")
            continue
        
        for f in p.glob('**/*'):
            if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                if any(f.match(pat) for pat in ignore_pats):
                    continue
                all_photo_paths.append(f)

                current_time = time.time()
                if current_time - last_discovery_log_time > 15:
                    elapsed = current_time - discovery_start_time
                    rate = len(all_photo_paths) / elapsed if elapsed > 0 else 0
                    logging.info(f"Discovered {len(all_photo_paths)} photos... Rate: {rate:.2f} files/sec")
                    last_discovery_log_time = current_time

    total_discovery_time = time.time() - discovery_start_time
    logging.info(f"Discovery finished. Found {len(all_photo_paths)} total photos in {total_discovery_time:.2f}s.")

    if not all_photo_paths:
        logging.info("No photos found to index.")
        return

    # 4. Determine work to be done
    jobs = []
    for path in all_photo_paths:
        db_entry = photos_in_db.get(str(path))
        needs_exif = db_entry is None or (db_entry['metadata_extraction_attempts'] is None or db_entry['metadata_extraction_attempts'] < 3)
        jobs.append((path, needs_exif))

    # 5. Process photos in parallel
    num_processes = max(1, cpu_count() // 2)
    total_jobs = len(jobs)
    logging.info(f"Starting photo processing for {total_jobs} photos with {num_processes} processes.")
    
    photos_processed = 0
    md5sums_computed = 0
    exif_data_collected = 0
    processing_start_time = time.time()
    last_processing_log_time = processing_start_time

    with Pool(processes=num_processes) as pool:
        for result in pool.imap_unordered(_process_photo_wrapper, jobs):
            if result:
                photo_path, md5sum, exif_data, md5_success, exif_success = result
                
                if md5_success:
                    md5sums_computed += 1
                if exif_success:
                    exif_data_collected += 1

                database.add_photo_to_index(photo_path, md5sum, exif_data, update_md5sum=update_md5sum)
                photos_processed += 1

                current_time = time.time()
                if current_time - last_processing_log_time > 15:
                    elapsed = current_time - processing_start_time
                    rate = photos_processed / elapsed if elapsed > 0 else 0
                    percentage = (photos_processed / total_jobs) * 100 if total_jobs > 0 else 0
                    
                    etc_str = ""
                    if rate > 0:
                        remaining_jobs = total_jobs - photos_processed
                        etc_seconds = remaining_jobs / rate
                        etc_str = f" ETC: {_format_time(etc_seconds)}"

                    logging.info(f"Processed {photos_processed}/{total_jobs} ({percentage:.1f}%) photos. Rate: {rate:.2f} records/sec.{etc_str}")
                    last_processing_log_time = current_time

    total_time = time.time() - processing_start_time
    logging.info("--------------------")
    logging.info("Indexing finished.")
    if total_time > 0:
        avg_rate = photos_processed / total_time
        logging.info(f"Processed {photos_processed} photos in {total_time:.2f}s. Average rate: {avg_rate:.2f} photos/sec")
    else:
        logging.info(f"Processed {photos_processed} photos.")
    
    logging.info(f"MD5 sums computed: {md5sums_computed}")
    logging.info(f"EXIF data collected: {exif_data_collected}")
    logging.info("--------------------")