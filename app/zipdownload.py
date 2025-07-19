import logging
import sqlite3
import uuid
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote_plus

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from . import database

log = logging.getLogger(__name__)

class ZipDownloader:
    def create_zip_for_tag(self, tag: str):
        decoded_tag = unquote_plus(tag)
        conn = database.get_db_connection()
        try:
            tag_pattern = f"%{decoded_tag}%"
            photos = conn.execute("SELECT path FROM photos WHERE tags LIKE ?", (tag_pattern,)).fetchall()
        except sqlite3.Error as e:
            log.error(f"Database error when fetching photos for tag {decoded_tag}: {e}")
            raise HTTPException(status_code=500, detail="Database error.")
        finally:
            conn.close()

        if not photos:
            raise HTTPException(status_code=404, detail="No photos found with this tag.")

        zip_io = BytesIO()
        filenames = set()

        with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for photo in photos:
                photo_path = Path(photo['path'])
                filename = photo_path.name
                if filename in filenames:
                    filename = f"{uuid.uuid4()}{photo_path.suffix}"
                filenames.add(filename)
                zipf.write(photo_path, arcname=filename)

        zip_io.seek(0)
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        zip_filename = f"photos_{decoded_tag}_{date_str}.zip"
        
        return StreamingResponse(
            iter([zip_io.getvalue()]),
            media_type="application/x-zip-compressed",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
