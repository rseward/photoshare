# Release Notes

## v0.3.0

### Features

- **Image Rotation:** Added clockwise and counter-clockwise rotation buttons to the photo slideshow.
- **Photo Deletion:** New script to interactively review and delete photos marked for deletion.
- **Tag Copying:** Added a command-line utility to copy tags between photo databases.
- **Indexer Update:** The indexer now detects and updates the path for moved photos.

## v0.2.0

### Features

- **Photo Deletion:** Added a `datetime_deleted` field to the database to track deleted photos. Created a new `delete_photos.py` script to interactively review and delete photos marked for deletion.
- **Image Rotation:** Added clockwise and counter-clockwise rotation buttons to the photo slideshow. The image file is rotated, and its md5sum is updated in the database.
- **Indexer Update:** The indexer now detects if a photo has been moved. If a photo with a known md5sum is found at a new path, the database record is updated with the new location.
- **Dependencies:** Replaced `opencv-python-headless` with `opencv-python` to support image display in the new deletion script.

### Other

- Improved database schema management in `app/database.py`.

## v0.1.1

### Features

- Parallelized indexing for faster performance.
- Database schema migrations and back-fills for timestamps.
- New tags page to view all tags.
- Dashboard updated with more slideshow options.
- New CLI tool to import photos.
- Slideshow UI improvements (pauses during tagging).
- Added md5sum to photos for content verification.
- Added dotenv support for environment variables.
- Added geolocation and time taken to photos.
- Added tag count caching layer.

### Bug Fixes

- Fixed a faulty wraparound in the untagged photo sequence.
- Fixed an incorrect test setup for the new photo sequence.

### Other

- Improved robustness of the photo indexing process.
- Separated CSS into `style.css`.

## v0.1.0

- Initial release
- Implemented a slideshow feature that displays random photos from the database.
- Implemented a dashboard feature that displays a summary of the photos in the database.
- Implemented a tag cloud feature that displays a word cloud of the tags in the database.
