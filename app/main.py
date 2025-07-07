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

@app.get("/photos/random", response_class=JSONResponse)
async def get_random_photo_details(request: Request, authorization: Optional[str] = Header(None)):
    api_key_env = os.environ.get("PHOTOSHARE_API_KEY")
    if not api_key_env:
        log.error("CRITICAL: PHOTOSHARE_API_KEY is not set on the server.")
        raise HTTPException(status_code=500, detail="Server is not configured for authentication.")
    
    if not authorization or authorization != f"Client-ID {api_key_env}":
        raise HTTPException(status_code=401, detail="Invalid or missing API Key.")

    conn = database.get_db_connection()
    try:
        photo = conn.execute("SELECT id, width, height FROM photos ORDER BY RANDOM() LIMIT 1").fetchone()
    except sqlite3.Error as e:
        log.error(f"Database error when fetching random photo: {e}")
        raise HTTPException(status_code=500, detail="Database error.")
    finally:
        conn.close()

    if not photo:
        raise HTTPException(status_code=404, detail="No photos found in the index.")

    base_url = str(request.base_url)
    photo_url = f"{base_url}photos/{photo['id']}"

    response_data = {
        "id": str(photo['id']),
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

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})