import click
import sqlite3
from app.database import init_db
from tqdm import tqdm

def get_photo_count(conn):
    """Returns the number of photos in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM photos")
    return cursor.fetchone()[0]

def get_photo_tags(conn):
    """Returns a dictionary mapping md5sum to a list of tags."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.md5sum, t.tag
        FROM photos p
        JOIN photo_tags pt ON p.id = pt.photo_id
        JOIN tags t ON pt.tag_id = t.id
    """)
    photo_tags_map = {}
    for md5sum, tag in cursor.fetchall():
        if md5sum not in photo_tags_map:
            photo_tags_map[md5sum] = []
        photo_tags_map[md5sum].append(tag)
    return photo_tags_map

@click.command()
@click.argument('source_db')
@click.argument('dest_db')
def copy_tags(source_db, dest_db):
    """
    Copies tags from a source photo database to a destination database
    for photos with matching md5sums.
    """
    source_conn = sqlite3.connect(source_db)
    dest_conn = sqlite3.connect(dest_db)

    init_db(source_db)
    init_db(dest_db)

    source_count = get_photo_count(source_conn)
    dest_count = get_photo_count(dest_conn)

    if source_count < dest_count:
        small_conn, large_conn = source_conn, dest_conn
        small_name, large_name = "source", "destination"
    else:
        small_conn, large_conn = dest_conn, source_conn
        small_name, large_name = "destination", "source"

    click.echo(f"Source database has {source_count} photos.")
    click.echo(f"Destination database has {dest_count} photos.")
    click.echo(f"Iterating over {small_name} database.")

    source_photo_tags = get_photo_tags(source_conn)
    
    dest_cursor = dest_conn.cursor()
    dest_cursor.execute("SELECT id, md5sum FROM photos")
    dest_photos = dest_cursor.fetchall()

    with tqdm(total=len(dest_photos), desc="Copying tags") as pbar:
        for photo_id, md5sum in dest_photos:
            if md5sum in source_photo_tags:
                tags_to_add = source_photo_tags[md5sum]
                for tag in tags_to_add:
                    dest_cursor.execute("INSERT OR IGNORE INTO tags (tag) VALUES (?)", (tag,))
                    dest_cursor.execute("SELECT id FROM tags WHERE tag = ?", (tag,))
                    tag_id_result = dest_cursor.fetchone()
                    if tag_id_result:
                        tag_id = tag_id_result[0]
                        dest_cursor.execute(
                            "INSERT OR IGNORE INTO photo_tags (photo_id, tag_id) VALUES (?, ?)",
                            (photo_id, tag_id)
                        )
            pbar.update(1)

    dest_conn.commit()
    click.echo(f"Tags copied successfully from {source_db} to {dest_db}")

    source_conn.close()
    dest_conn.close()

if __name__ == '__main__':
    copy_tags()
