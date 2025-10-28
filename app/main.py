import random
import logging
import os
import sqlite3
import threading
from typing import Optional
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import quote_plus, unquote_plus

from . import caching, database, indexing, zipdownload, image_processing

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', filename='photoshare.log', filemode='a')
log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    database.init_db()
    log.info("Application startup complete.")
    
    # Start the background cache refresh
    caching.start_background_refresh()

    # Check for a lock file and start the indexer if needed
    db_file = os.environ.get("PHOTOSHARE_DATABASE_FILE", "photoshare.db")
    lock_file = Path(db_file).parent / "index.lock"
    if not lock_file.exists():
        log.info("No lock file found. Starting background indexing thread.")
        thread = threading.Thread(target=indexing.run_indexing, daemon=True)
        thread.start()
    else:
        log.info("Lock file found. Assuming external indexer is running.")
    yield

app = FastAPI(lifespan=lifespan)

# Apply a wide-open CORS policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization"], # Explicitly allow only the required header
)

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Add favicon endpoint
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(Path(__file__).parent / "static" / "favicon.ico")

def _get_photo_response(photo: sqlite3.Row, request: Request):
    if not photo:
        return None
    base_url = str(request.base_url)
    photo_url = f"{base_url}photos/{photo['id']}"
    return {
        "id": photo['id'],
        "filename": Path(photo['path']).name,
        "width": photo['width'],
        "height": photo['height'],
        "tags": photo['tags'],
        "datetime_taken": photo['datetime_taken'],
        "geolocation": photo['geolocation'],
        "urls": {"raw": photo_url, "full": photo_url, "regular": photo_url, "small": photo_url, "thumb": photo_url},
        "links": {"self": photo_url, "html": photo_url, "download": photo_url}
    }

@app.get("/photos/untagged", response_class=JSONResponse)
async def get_untagged_photos(
    request: Request,
    authorization: Optional[str] = Header(None),
    limit: int = 20
):
    # Authentication
    api_key_env = os.environ.get("PHOTOSHARE_API_KEY")
    if not api_key_env or not authorization or authorization != f"Client-ID {api_key_env}":
        raise HTTPException(status_code=401, detail="Invalid or missing API Key.")

    conn = database.get_db_connection()
    try:
        query = "SELECT * FROM photos WHERE tags IS NULL OR tags = '' ORDER BY RANDOM() LIMIT ?"
        
        photos_cursor = conn.execute(query, (limit,))
        photos = photos_cursor.fetchall()

    except sqlite3.Error as e:
        log.error(f"Database error in /photos/untagged: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    if not photos:
        return JSONResponse(content={"photos": []})
    
    # Process photos to include full URLs
    photo_responses = [_get_photo_response(photo, request) for photo in photos]

    return JSONResponse(content={"photos": photo_responses})


@app.get("/photos/random", response_class=JSONResponse)
async def get_random_photo_details(
    request: Request,
    authorization: Optional[str] = Header(None),
    tag: Optional[str] = None
):
    # Authentication
    api_key_env = os.environ.get("PHOTOSHARE_API_KEY")
    if not api_key_env or not authorization or authorization != f"Client-ID {api_key_env}":
        raise HTTPException(status_code=401, detail="Invalid or missing API Key.")

    conn = database.get_db_connection()
    try:
        query = "SELECT * FROM photos"
        params = []
        if tag:
            query += " WHERE tags LIKE ?"
            params.append(f"%{tag}%")
        query += " ORDER BY RANDOM() LIMIT 1"
        
        photo = conn.execute(query, tuple(params)).fetchone()
    except sqlite3.Error as e:
        log.error(f"Database error in /photos/random: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    if not photo:
        raise HTTPException(status_code=404, detail="No photos found.")
    
    return JSONResponse(content=_get_photo_response(photo, request))

@app.get("/photos/sequence/{sequence_name}", response_class=JSONResponse)
async def get_photo_sequence(
    request: Request,
    sequence_name: str,
    authorization: Optional[str] = Header(None),
    current_photo_id: Optional[int] = None,
    direction: Optional[str] = None,
    shuffle_id: Optional[int] = None
):
    # Authentication
    api_key_env = os.environ.get("PHOTOSHARE_API_KEY")
    if not api_key_env or not authorization or authorization != f"Client-ID {api_key_env}":
        raise HTTPException(status_code=401, detail="Invalid or missing API Key.")

    base_query = "SELECT * FROM photos"
    where_clauses = []
    params = []

    # Base filter for the sequence
    if sequence_name == 'new':
        where_clauses.append("datetime_added IS NOT NULL AND datetime_added != ''")
        order_by_main = "ORDER BY datetime_added DESC, id DESC"
        order_by_rev = "ORDER BY datetime_added ASC, id ASC"
    elif sequence_name == 'tagged':
        where_clauses.append("tags IS NOT NULL AND tags != ''")
        order_by_main = "ORDER BY id ASC"
        order_by_rev = "ORDER BY id DESC"
    elif sequence_name == 'untagged':
        where_clauses.append("tags IS NULL OR tags = ''")
        order_by_main = "ORDER BY id ASC"
        order_by_rev = "ORDER BY id DESC"
    elif sequence_name == 'shuffle':
        # Generate shuffle_id if not provided
        if shuffle_id is None:
            shuffle_id = random.randint(100, 10000)
        order_by_main = f"ORDER BY (id % {shuffle_id}), id"
        order_by_rev = f"ORDER BY (id % {shuffle_id}) DESC, id DESC"
    else:
        raise HTTPException(status_code=404, detail="Unknown sequence name.")

    conn = database.get_db_connection()
    try:
        if direction and current_photo_id:
            current_photo = conn.execute("SELECT id, datetime_added FROM photos WHERE id = ?", (current_photo_id,)).fetchone()
            if not current_photo:
                raise HTTPException(status_code=404, detail="Current photo not found.")

            if sequence_name == 'new':
                current_val = current_photo['datetime_added']
                if direction == 'next':
                    where_clauses.append("(datetime_added < ? OR (datetime_added = ? AND id < ?))")
                    params.extend([current_val, current_val, current_photo_id])
                    order_by = order_by_main
                else: # previous
                    where_clauses.append("(datetime_added > ? OR (datetime_added = ? AND id > ?))")
                    params.extend([current_val, current_val, current_photo_id])
                    order_by = order_by_rev
            elif sequence_name == 'shuffle':
                # For shuffle mode, navigate based on mod value
                current_mod = current_photo_id % shuffle_id
                if direction == 'next':
                    where_clauses.append("((id % ?) > ? OR ((id % ?) = ? AND id > ?))")
                    params.extend([shuffle_id, current_mod, shuffle_id, current_mod, current_photo_id])
                    order_by = order_by_main
                else: # previous
                    where_clauses.append("((id % ?) < ? OR ((id % ?) = ? AND id < ?))")
                    params.extend([shuffle_id, current_mod, shuffle_id, current_mod, current_photo_id])
                    order_by = order_by_rev
            else: # Navigation by ID for tagged/untagged
                if direction == 'next':
                    where_clauses.append("id > ?")
                    params.append(current_photo_id)
                    order_by = order_by_main
                else: # previous
                    where_clauses.append("id < ?")
                    params.append(current_photo_id)
                    order_by = order_by_rev

            where_clauses.append("datetime_deleted IS NULL OR datetime_deleted = ''")

            query = f"{base_query} WHERE {' AND '.join(where_clauses)} {order_by} LIMIT 1"
            photo = conn.execute(query, tuple(params)).fetchone()

        else:
            # Initial load of the sequence
            if sequence_name == 'new':
                # Get top 1000 newest photos and pick one at random
                top_1000_query = f"SELECT id FROM photos WHERE {' AND '.join(where_clauses)} {order_by_main} LIMIT 1000"
                top_1000_ids = [row['id'] for row in conn.execute(top_1000_query, tuple(params)).fetchall()]
                if not top_1000_ids:
                    raise HTTPException(status_code=404, detail="No new photos found.")

                random_id = random.choice(top_1000_ids)
                query = f"{base_query} WHERE id = ?"
                photo = conn.execute(query, (random_id,)).fetchone()
            elif sequence_name == 'shuffle':
                # For shuffle, start from the first photo in shuffle order
                where_clauses.append("datetime_deleted IS NULL OR datetime_deleted = ''")
                order_by = order_by_main
                query = f"{base_query} WHERE {' AND '.join(where_clauses)} {order_by} LIMIT 1"
                photo = conn.execute(query, tuple(params)).fetchone()
            else:
                # Original logic for other sequences
                where_clauses.append("datetime_deleted IS NULL OR datetime_deleted = ''")
                order_by = order_by_main
                query = f"{base_query} WHERE {' AND '.join(where_clauses)} {order_by} LIMIT 1"
                photo = conn.execute(query, tuple(params)).fetchone()

        # Handle wraparound
        if not photo and direction:
            # The base query for a sequence never has parameters
            wrap_query = f"{base_query} WHERE {where_clauses[0]} {order_by_main if direction == 'next' else order_by_rev} LIMIT 1"
            photo = conn.execute(wrap_query).fetchone()

    except sqlite3.Error as e:
        log.error(f"Database error in /photos/sequence: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    if not photo:
        raise HTTPException(status_code=404, detail="No photos found for this sequence.")

    response_data = _get_photo_response(photo, request)

    # Include shuffle_id in response for shuffle mode
    if sequence_name == 'shuffle':
        response_data['shuffle_id'] = shuffle_id

    return JSONResponse(content=response_data)


@app.get("/photos/{photo_id}")
async def get_photo_file(photo_id: int):
    conn = database.get_db_connection()
    try:
        photo = conn.execute("SELECT path FROM photos WHERE id = ?", (photo_id,)).fetchone()
    except sqlite3.Error as e:
        logging.error(f"Database error when fetching photo by ID {photo_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()
        
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found.")
    
    return FileResponse(photo['path'])

@app.post("/photo/delete/{photo_id}", status_code=204)
async def mark_photo_for_deletion(photo_id: int, authorization: Optional[str] = Header(None)):
    # Authentication
    api_key_env = os.environ.get("PHOTOSHARE_API_KEY")
    if not api_key_env or not authorization or authorization != f"Client-ID {api_key_env}":
        raise HTTPException(status_code=401, detail="Invalid or missing API Key.")

    conn = database.get_db_connection()
    try:
        photo = conn.execute("SELECT path FROM photos WHERE id = ?", (photo_id,)).fetchone()
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found in index.")
        
        db_dir = Path(database.get_db_path()).parent
        delete_file = db_dir / "photos_to_delete.txt"
        with open(delete_file, "a") as f:
            f.write(f"{photo['path']}\n")
        
        conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
        log.info(f"Marked and removed photo {photo_id}")

    except sqlite3.Error as e:
        log.error(f"Database error during photo deletion: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    return {}

@app.post("/photo/tag/{photo_id}", status_code=204)
async def tag_photo(photo_id: int, request: Request, authorization: Optional[str] = Header(None)):
    # Authentication
    api_key_env = os.environ.get("PHOTOSHARE_API_KEY")
    if not api_key_env or not authorization or authorization != f"Client-ID {api_key_env}":
        raise HTTPException(status_code=401, detail="Invalid or missing API Key.")

    try:
        data = await request.json()
        tags = data.get("tags")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body.")

    if tags is None:
        raise HTTPException(status_code=400, detail="Missing 'tags' in request body.")

    conn = database.get_db_connection()
    try:
        conn.execute("UPDATE photos SET tags = ? WHERE id = ?", (tags, photo_id))
        conn.commit()
        log.info(f"Tagged photo {photo_id} with: '{tags}'")
    except sqlite3.Error as e:
        log.error(f"Database error during photo tagging: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    return {}


@app.post("/photo/rotate/{photo_id}", response_class=JSONResponse)
async def rotate_photo(photo_id: int, request: Request, authorization: Optional[str] = Header(None)):
    # Authentication
    api_key_env = os.environ.get("PHOTOSHARE_API_KEY")
    if not api_key_env or not authorization or authorization != f"Client-ID {api_key_env}":
        raise HTTPException(status_code=401, detail="Invalid or missing API Key.")

    try:
        data = await request.json()
        direction = data.get("direction")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body.")

    if direction not in ['cw', 'ccw']:
        raise HTTPException(status_code=400, detail="Invalid rotation direction.")

    conn = database.get_db_connection()
    try:
        photo = conn.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found.")

        new_md5sum = image_processing.rotate_image(photo['path'], direction)

        if new_md5sum:
            conn.execute("UPDATE photos SET md5sum = ? WHERE id = ?", (new_md5sum, photo_id))
            conn.commit()
            log.info(f"Rotated photo {photo_id} ({direction}) and updated md5sum.")
            # Re-fetch the photo to get the updated data
            updated_photo = conn.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
            return JSONResponse(content=_get_photo_response(updated_photo, request))
        else:
            raise HTTPException(status_code=500, detail="Failed to rotate image.")

    except sqlite3.Error as e:
        log.error(f"Database error during photo rotation: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()


@app.get("/ui/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serves the dashboard HTML page."""
    conn = database.get_db_connection()
    try:
        photo_count = conn.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        tagged_photo_count = conn.execute("SELECT COUNT(*) FROM photos WHERE tags IS NOT NULL AND tags != ''").fetchone()[0]
        
        random_photo = conn.execute("SELECT id FROM photos ORDER BY RANDOM() LIMIT 1").fetchone()
        background_image_url = f"/photos/{random_photo['id']}" if random_photo else ""

    except sqlite3.Error as e:
        log.error(f"Database error on dashboard: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    tag_counts = caching.get_tag_counts()
    sorted_tags = sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)
    top_30_tags = dict(sorted_tags[:30])
    max_count = max(top_30_tags.values()) if top_30_tags else 0
    tag_cloud = [
        {
            "text": tag,
            "size": 1 + (count / max_count * 1.5) if max_count > 0 else 1,
            "count": count,
            "encoded_text": quote_plus(tag)
        }
        for tag, count in top_30_tags.items()
    ]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "photo_count": photo_count,
        "tagged_photo_count": tagged_photo_count,
        "tag_cloud": tag_cloud,
        "background_image_url": background_image_url
    })


@app.get("/", response_class=RedirectResponse)
async def read_root():
    """Redirects the root URL to the slideshow page."""
    return RedirectResponse(url="/ui/dashboard")

@app.get("/ui/slideshow", response_class=HTMLResponse)
async def slideshow(request: Request):
    """Serves the main random slideshow HTML page."""
    api_key = os.environ.get("PHOTOSHARE_API_KEY", "")
    google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "api_key": api_key, 
        "google_maps_api_key": google_maps_api_key,
        "slideshow_type": "random",
        "tag": None
    })

@app.get("/ui/slideshow/{tag}", response_class=HTMLResponse)
async def slideshow_by_tag(request: Request, tag: str):
    """Serves the slideshow HTML page filtered by tag or special sequence."""
    api_key = os.environ.get("PHOTOSHARE_API_KEY", "")
    google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    decoded_tag = unquote_plus(tag)
    
    special_filters = ['new', 'tagged', 'untagged']
    slideshow_type = "sequence" if decoded_tag in special_filters else "random"
    
    conn = database.get_db_connection()
    try:
        if decoded_tag == 'new':
            tag_photo_count = conn.execute("SELECT COUNT(*) FROM photos WHERE datetime_added IS NOT NULL AND datetime_added != ''").fetchone()[0]
        elif decoded_tag == 'tagged':
            tag_photo_count = conn.execute("SELECT COUNT(*) FROM photos WHERE tags IS NOT NULL AND tags != ''").fetchone()[0]
        elif decoded_tag == 'untagged':
            tag_photo_count = conn.execute("SELECT COUNT(*) FROM photos WHERE tags IS NULL OR tags = ''").fetchone()[0]
        else:
            tag_pattern = f"%{decoded_tag}%"
            tag_photo_count = conn.execute("SELECT COUNT(*) FROM photos WHERE tags LIKE ?", (tag_pattern,)).fetchone()[0]
    except sqlite3.Error as e:
        log.error(f"Database error when counting photos for tag {decoded_tag}: {e}")
        tag_photo_count = 0
    finally:
        conn.close()

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "api_key": api_key, 
        "google_maps_api_key": google_maps_api_key,
        "slideshow_type": slideshow_type,
        "tag": decoded_tag,
        "tag_photo_count": tag_photo_count
    })


@app.get("/ui/tags", response_class=HTMLResponse)
async def tags_page(request: Request, sort_by: str = 'tag', order: str = 'asc', search: str = ''):
    """Serves the page that lists all tags."""
    conn = database.get_db_connection()
    try:
        random_photo = conn.execute("SELECT id FROM photos ORDER BY RANDOM() LIMIT 1").fetchone()
        background_image_url = f"/photos/{random_photo['id']}" if random_photo else ""
    except sqlite3.Error as e:
        log.error(f"Database error on tags page: {e}")
        background_image_url = ""
    finally:
        conn.close()

    tags = database.get_all_tags(sort_by=sort_by, order=order, search=search)
    return templates.TemplateResponse("tags.html", {
        "request": request,
        "tags": tags,
        "sort_by": sort_by,
        "order": order,
        "search": search,
        "background_image_url": background_image_url
    })


@app.get("/download/tagged/{tag}", response_class=StreamingResponse)
async def download_tagged_photos(tag: str):
    """Downloads all photos with a specific tag as a zip file."""
    downloader = zipdownload.ZipDownloader()
    return downloader.create_zip_for_tag(tag)