#!/usr/bin/env python

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
        SELECT p.md5sum, tags
        FROM photos p
    """)
    photo_tags_map = {}
    for md5sum, tag in cursor.fetchall():
        if md5sum not in photo_tags_map:
            photo_tags_map[md5sum] = []
        photo_tags_map[md5sum].append(tag)
    return photo_tags_map

def get_photo_tag_counts(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT count(1) FROM photos WHERE tags IS NOT NULL")
    return cursor.fetchone()[0]

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

    small_cursor = small_conn.cursor()
    small_cursor.execute("SELECT id, md5sum FROM photos")
    small_photos = small_cursor.fetchall()

    with tqdm(total=len(small_photos), desc="Copying tags") as pbar:
        for photo_id, md5sum in small_photos:
            if md5sum in source_photo_tags:
                tags_to_add = source_photo_tags[md5sum]
                for tag in tags_to_add:
                    dest_cursor.execute("UPDATE photos SET tags = ? WHERE md5sum = ?", (tag, md5sum))
            pbar.update(1)

    dest_conn.commit()
    click.echo(f"Tags copied successfully from {source_db} to {dest_db}")

    dst_tag_count = get_photo_tag_counts(dest_conn)
    click.echo(f"Destination database now has {dst_tag_count} photos with tags.")

    source_conn.close()
    dest_conn.close()

if __name__ == '__main__':
    copy_tags()
