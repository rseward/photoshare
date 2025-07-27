# Release Notes

## v0.2.0

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