#!/usr/bin/env python

import click
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up imports for the application modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
from app import indexing, database

# Configure logging to print to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@click.group()
def cli():
    """A command-line tool for managing the PhotoShare index."""
    pass

@cli.command()
@click.option('--md5sum', '-m', is_flag=True, help='Update md5sum for existing photos.')
def index(md5sum):
    """
    Scans photo directories and builds the database index.
    Creates a lock file to prevent the web service from starting a duplicate scan.
    """
    db_file = os.environ.get("PHOTOSHARE_DATABASE_FILE", "photoshare.db")
    lock_file = Path(db_file).parent / "index.lock"

    if lock_file.exists():
        click.echo("Lock file exists. Another indexing process may be running.")
        raise click.Abort()

    try:
        # Create lock file
        lock_file.touch()
        click.echo(f"Created lock file at {lock_file}")

        # Initialize DB and run indexing
        database.init_db()
        indexing.run_indexing(update_md5sum=md5sum)

    finally:
        # Ensure lock file is removed
        if lock_file.exists():
            lock_file.unlink()
            click.echo(f"Removed lock file at {lock_file}")

if __name__ == '__main__':
    cli()
