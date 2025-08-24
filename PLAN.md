# Project Goals

Implement a photo sharing web service that allows users to view photos from a collection with their friends and family.

The web service will expose an API compatible with the unsplash API and provide a web interface to view the photos.

  - https://unsplash.com/documentation
  - https://github.com/unsplash/unsplash-js


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

## Photo Preview Requirements

- The root / index page of the web service will serve up a slide show of random photos from the collection
- The root page should have a minimal design with a dark theme
- The root page should embed the configured SHAREPHOTO_API_KEY in the html or JS. So it works automatically with the API backend.
- The root page should expand photos to full size when loaded.
- A new photo should be pulled from the API every 30 seconds automatically.
- The root page should overlay the current date and time at the bottom of the photo.
- The root page should overlay the photo's name at the top of the photo.
- The slide show interface shall provide a pause / resume toggle button near the center of the time display bar at the bottom of the photo. While the slideshow is running pressing pause will pause the slideshow and toggle to a resume button and pressing resume will resume the slideshow and toggle back to a pause button.
- The slide show interface shall provide next and previous buttons. The previous button appears to the center left edge of the time display bar and the next button appears to the right edge of the "time display bar".
- The slide show interface shall provide a delete button to mark a photo for deletion. The button will appear on the left edge of the file name bar at the top of the photo. When pressed the button will call a backend endpoint, /photo/delete/{photo_id} to append the full path of the photo identified by the ID to a file named photos_to_delete.txt in the same directory as the database.
- The slide show interface shall provide a tag input box that will allow the user to tag the photo with arbitary text in the database. Create a new tag field in the database and add the tag to the photo in the database. Pressing enter in the field will send the tag to the backend endpoint, /photo/tag/{photo_id}. The tag input field will appear on the right hand side of the file name bar at the top of the photo. The field will accomodate at least 30 characters.

## copytags

- Implemented a python CLI utility to copy tags from one photo database to another.
- Used the click library to create a CLI utility.
- The utility takes two arguments, the source database and the destination database.
- The utility copies all tags from the source database to the destination database for photos that have the same md5sum.
- Wrote a permanent unittest to test the copytags feature.
- Verified that the copytags features works by running and resolving the unittest failures.




## Future Enhancements

- To be defined
