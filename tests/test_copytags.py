#!/usr/bin/env python

import os
import sys
import sqlite3
import unittest

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from copytags import copy_tags
from app.database import init_db

class TestCopyTags(unittest.TestCase):
    """
    Unittest to call copytags.copy_tags function directly for testing.
    """

    def setUp(self):
        self.source_db = 'test_source.db'
        self.dest_db = 'test_dest.db'

        # Setup source database
        self.source_conn = sqlite3.connect(self.source_db)
        init_db(self.source_db)
        self.source_cursor = self.source_conn.cursor()
        self.source_cursor.execute("INSERT INTO photos (md5sum, path, width, height, tags) VALUES (?, ?, ?, ?, ?)", ('md5_1', 'path/to/photo1', 0, 0, 'tag1 tag2'))
        self.source_cursor.execute("INSERT INTO photos (md5sum, path, width, height, tags) VALUES (?, ?, ?, ?, ?)", ('md5_2', 'path/to/photo2', 0, 0, None))
        #self.source_cursor.execute("INSERT INTO tags (tag) VALUES (?)", ('tag1',))
        #self.source_cursor.execute("INSERT INTO tags (tag) VALUES (?)", ('tag2',))
        #self.source_cursor.execute("INSERT INTO photo_tags (photo_id, tag_id) VALUES (?, ?)", (1, 1))
        #self.source_cursor.execute("INSERT INTO photo_tags (photo_id, tag_id) VALUES (?, ?)", (1, 2))
        self.source_conn.commit()

        # Setup destination database
        self.dest_conn = sqlite3.connect(self.dest_db)
        init_db(self.dest_db)
        self.dest_cursor = self.dest_conn.cursor()
        self.dest_cursor.execute("INSERT INTO photos (md5sum, path, width, height) VALUES (?, ?, ?, ?)", ('md5_1', 'another/path/to/photo1', 0, 0))
        self.dest_cursor.execute("INSERT INTO photos (md5sum, path, width, height) VALUES (?, ?, ?, ?)", ('md5_3', 'path/to/photo3', 0, 0))
        self.dest_conn.commit()

    def tearDown(self):
        self.source_conn.close()
        self.dest_conn.close()
        os.remove(self.source_db)
        os.remove(self.dest_db)

    def test_copy_tags(self):
        copy_tags.callback(self.source_db, self.dest_db)

        # Verify tags were copied
        self.dest_cursor.execute("""
            SELECT p.tags
            FROM photos p
            WHERE p.md5sum = 'md5_1'
        """)
        tags = {row[0] for row in self.dest_cursor.fetchall()}
        self.assertEqual(tags, {'tag1 tag2'})

        # Verify photo without matching md5sum was not tagged
        self.dest_cursor.execute("SELECT COUNT(*) FROM photos WHERE id = 2 AND tags IS NOT NULL")
        count = self.dest_cursor.fetchone()[0]
        self.assertEqual(count, 0)

if __name__ == '__main__':
    unittest.main()