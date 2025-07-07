# Project Goals

Implement a photo sharing web service that allows users to view photos from a collection with their friends and family.

The web service will expose an API compatible with the unsplash API and provide a web interface to view the photos.

  - https://unsplash.com/documentation
  - https://github.com/unsplash/unsplash-js

This project was/is a collaboration between me and gemini-cli. Gemini-cli have spent approximately 4 man-hours (my time) on the project so far. This has been a project I have wanted to implement for some time. I have a magic-mirror on my desk with plugins to pull images from unsplash. My goal is to alter that plugin to pull images from my photo collection instead of unsplash using this application.

## Technical Requirements

- The application will be written in Python.
- The application will use the FastAPI or Flask frameworks which ever is more appropriate for the task.
- The application will implament a unsplash compatible API for fetching photos.
- An unsplash API like key will be required to use the application.
- An unsplash compatible javascript client should be able to connect to the web service and fetch photos as if it was connecting to the unsplash API.
- The web service will be configured via environment variables.
- The web service will be given a set of directories to fetch photos from.
- The web service will randomly select a photo from the directories and serve it as if it was fetched from the unsplash API.
- A log of the selected photos will be written to a log file.
- The web service will be able to run in a docker container.
- If photo manipulations are required use opencv to perform the manipulations.

## Photo Indexing Requirments

- The web service will index photos recursively in the directories.
- The photo indexing will happen asynchrounously at startup in a background thread.
- The web service will make photos eligible for selection from the index as they are discovered.
- The index will be stored as a sqlite database.
- The web service threads will make photo selections from the sqlite database index.
- The background indexing thread will update the sqlite database index as photos are added or removed from the directories.
- The index will use the photo file name path as a unique key for the table. The background indexing thread will add or update photos as they changes in the directories after startup. The indexing thread should exit after discovering it's last photo. The indexing thread should perform record updates in batches of 100 records for it's first batch and then 1000 records for all subsequent batches.
- The index should be able to be updated as photos are added or removed from the directories on application start up.
- Photo indexer should be able to read a list of patterns to ignore from a file specified by the PHOTOSHARE_PHOTO_IGNORE_PATS environment variable.
- Periodically log the number of photos discovered and the photos discovered per second metric to the log file during the indexing.
- Allow the indexing thread to be run in a seperate process by providing a click command line interface to start the indexing thread. If a index.lock file exists the web service will not start the indexing thread.



## Future Enhancements

- To be defined
