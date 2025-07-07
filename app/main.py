import logging
import os
import sqlite3
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from . import database, indexing

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

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

from typing import Optional

@app.get("/photos/random", response_class=JSONResponse)
async def get_random_photo_details(
    request: Request, 
    authorization: Optional[str] = Header(None),
    current_photo_id: Optional[int] = None,
    direction: Optional[str] = None
):
    # Simplified, manual authentication check
    api_key_env = os.environ.get("PHOTOSHARE_API_KEY")
    if not api_key_env:
        raise HTTPException(status_code=500, detail="Server not configured for authentication.")
    
    if not authorization or authorization != f"Client-ID {api_key_env}":
        raise HTTPException(status_code=401, detail="Invalid or missing API Key.")

    conn = database.get_db_connection()
    try:
        if direction and current_photo_id is not None:
            if direction == "next":
                query = "SELECT id, path, width, height FROM photos WHERE id > ? ORDER BY id ASC LIMIT 1"
                photo = conn.execute(query, (current_photo_id,)).fetchone()
                # If we're at the end, loop back to the first photo
                if not photo:
                    photo = conn.execute("SELECT id, path, width, height FROM photos ORDER BY id ASC LIMIT 1").fetchone()
            elif direction == "previous":
                query = "SELECT id, path, width, height FROM photos WHERE id < ? ORDER BY id DESC LIMIT 1"
                photo = conn.execute(query, (current_photo_id,)).fetchone()
                # If we're at the beginning, loop back to the last photo
                if not photo:
                    photo = conn.execute("SELECT id, path, width, height FROM photos ORDER BY id DESC LIMIT 1").fetchone()
            else: # Default to random if direction is invalid
                photo = conn.execute("SELECT id, path, width, height FROM photos ORDER BY RANDOM() LIMIT 1").fetchone()
        else:
             # Fetch a random photo from the database
            photo = conn.execute("SELECT id, path, width, height FROM photos ORDER BY RANDOM() LIMIT 1").fetchone()

    except sqlite3.Error as e:
        log.error(f"Database error when fetching photo: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    if not photo:
        raise HTTPException(status_code=404, detail="No photos found in the index.")

    base_url = str(request.base_url)
    photo_url = f"{base_url}photos/{photo['id']}"

    response_data = {
        "id": photo['id'],
        "filename": Path(photo['path']).name,
        "width": photo['width'],
        "height": photo['height'],
        "urls": {"raw": photo_url, "full": photo_url, "regular": photo_url, "small": photo_url, "thumb": photo_url},
        "links": {"self": photo_url, "html": photo_url, "download": photo_url}
    }
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
        # First, get the path of the photo to be deleted
        photo = conn.execute("SELECT path FROM photos WHERE id = ?", (photo_id,)).fetchone()
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found in index.")
        
        photo_path_to_delete = photo['path']

        # Append the path to the deletion file
        db_dir = Path(database.get_db_path()).parent
        delete_file = db_dir / "photos_to_delete.txt"
        with open(delete_file, "a") as f:
            f.write(f"{photo_path_to_delete}\n")
        log.info(f"Marked photo for deletion: {photo_path_to_delete}")

        # Then, remove the photo from the database
        conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
        log.info(f"Removed photo from index: {photo_id}")

    except sqlite3.Error as e:
        log.error(f"Database error during photo deletion: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    return {}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    api_key = os.environ.get("PHOTOSHARE_API_KEY", "")
    return templates.TemplateResponse("index.html", {"request": request, "api_key": api_key})