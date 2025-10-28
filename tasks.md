# Project

A simple lightweight web photosharing app

## Pending Tasks

### photo slideshow features

- For untagged, tagged and new photo slideshow modes, don't stop at the last photo, instead loop back to the first photo in the sequence.

## Completed Tasks

### photo slideshow features

- Improve the shuffle slide show feature by generating a random number for a web browser session (shuffle_id). The backend sends the shuffle_id when a browser starts a shuffled slideshow session. The web browser appends this shuffle_id to the backend slideshow endpoint URL parameters. The backend uses the shuffle_id to give an orderly progression of photos back to the client, allowing easy back and forth navigation. Implemented using queries like `ORDER BY (id % shuffle_id), id` where shuffle_id is a random number between 100-10000.
- Add two rotation buttons to the slideshow. One to rotate the photo clockwise and one to rotate the photo counter clockwise.
- Pressing the rotate button will rotate the photo 90 degrees clockwise or counter clockwise. The new md5sum of the photo will be computed and the database record will be updated for the photo.
- The rotation buttons will be hidden by default. They will only be shown when the user hovers over the photo.
- seperate the slideshow features into the own seperate end points to make the logic more modular.
- Revise the new photo end point to query the database for the top 1000 photos ordered by datetime_added descending. Select a random photo from this result and return that photo from the "new" endpoint.
- Create a new unit test for the new photo end point. Verify when the end point is executed in sequence it does not return the same photo.

### database features

- Add a "datetime_deleted" field in the database to record when a photo is permanently deleted from the photoshare.
  The default value is null, and is populated with a ISO date time string when the file corresponding to the
  file is deleted with the delete_photos.py script.

### photo import features

- Modify indexer.py. When a file is discovered with a duplicate md5sum in the database, check to see if the path name
  is different from the path recorded in the database record. When such a file is discovered, update it's path in the 
  database record. Leave all other information in the record as is. An identical md5sum with different paths indicates the files was moved between
  photo indexe scans.

### photo deletion features

- Please fix this problem with marking a photo for deletion in the slideshow. Advance to the next photo in the slideshow, before marking the photo selected by the user.

### delete reviewer

- Write a python script called delete_photos.py. The script will review the photos_to_delete.txt file. The script will use opencv's highgui to display the photos to delete.
  Text will be overlayed at the bottom to say "Press d to delete or s to skip. 23 / 170 photos reviewed". If the user presses "s", the photo will be skipped and the next photo from the list will be shown.
  Any tag text and EX/IF information for the photo will be displayed at the top of the image.
  If the user presses "d", the file will be moved to the /tmp/ directory. The file will be removed from the deletion list. The photo's datetime_deleted field will be set to the current date in the database. After the last photo has been reviewed the remaining photos (those that were skipped) will be written to the photos_to_delete.txt
  file.

### dashboard features

- Revise the dashboard to have a "View New Photos" button that links to a slideshow page that displays photos that have most recently been added to the database.
- Revise the dashboard to have a "View All Tagged Photos" button that links to a slideshow page that displays photos that have been tagged.
- Revise the dashboard to have a "View All Untagged Photos" button that links to a slideshow page that displays photos that have not yet been tagged.
- Arrange the dashboard "view" buttons in a grid of 3 columns and 2 rows.

### general geatures

- At the bottom of the dashboard a tag cloud should appear. The tag cloud should be generated from the tags in the database. The size of each tag in the cloud should be proportional to the number of photos that have that tag.
- Load and display any tags created for a photo when displaying the photo on the index.html page
- Create a /photos/bytag/{tag} end point. Randomly select a photo with that tag to send to the calling entity. E.g. this endpoint is used to create a slideshow of random photos matching that tag.
- Refactor the main landing index.html page. Move it's URL to /ui/slideshow
- When the root URL / is accessed redirect the browser to the new /ui/slideshow URL.
- Provide a slideshow page identical to the main /ui/slideshow/ URL that displays random photos that have been tagged with a specified tag.
  The URL to access this mode will be /ui/slideshow/{tag}
- Create a /ui/dashboard URL / page that displays a summary of the photos in the database. The background to the page should be a randomly selected photo from the database.
- On the dashboard a promenient transparent button should be provided to link the user to the /ui/slideshow URL.
- On the dashboard a tag input field should be provided to allow the user to enter a tag and then link to the /ui/slideshow/{tag} URL.
- Modify the "TAG word cloud" such that only the top 30 tags are displayed. Make each tag in the cloud be a clickable link to the /ui/slideshow/{tag} URL.
- In the "TAG word cloud" add a tooltip that displays the number of photos that have that tag. Also url encode the TAG text for it's slideshow URL.
- Alter the /ui/slideshow/{tag} URL to invert the url_plus functions escaping of the TAG text and use the decoded TAG text to create the slideshow.
- Add a home icon using app/static/imgs/home-icon-cropped-392x392.png to the top left of the dashboard and slideshow pages. On the slideshow page push the delete button slightly to the right of the home icon. Scale the icon image to 50x50 pixels. The home icon should be a link to the /ui/dashboard url.
- Revise the dashboard to show the number of photos in the database, and also the total number of tagged photos in the database.
- On a slideshow page with a tag filter applied, the page should show the number of photos that have that tag.
- On a slideshow page with a tag filter applied, a hamburger icon/menu should be shown. The first option on the menu should be a "Download Tagged Photos" option. This option should download all photos that have that tag to a zip file. The zip file should be named after the tag and the current date using this template photos_{tag}_{date}.zip. If there are image filename conflicts in the zip file, resolve them by naming the second file with a randomly generated guid with the photo extension.
- Modify the indexer so that it will extract the geolocation and date_time from the photo file and store it in the database. Update existing enteries and insert the information for new photos.
- datetime values are stored to the database as ISO 8601 strings.
- Modify the indexer to record the time new photos are added to the database by setting thedatetime_added field.
- Modify the slideshow to display datetime the photo was taken.
- Modify the slideshow to use javascript to translate geolocation coordingates to an approximate place name if available. Fetch the place name in the background after the photo is displayed. Use the Google Maps API to translate the geolocation to a place name.
- Use the existing db fields: geolocation, datetime_taken, datetime_added 
- Add a slideshow menu option to download the current image to the user's computer.
- The time taken and geolocation information is not being displayed, please resolve this. Only display the information if it is available. Perform the geocode lookup in the background after the photo is displayed. Use the Google Maps Geocode API to translate the geolocation to a place name.
- Revise the indexer to only update datetime_taken and geolocation information if the datetime_taken field is null for a photo.

### photo import feature

- Create a related CLI importphotos.py tool for use in importing photos from a specified path into the database. The tool will sort the incoming photos into two subdirectories within the specified path:
  1) new - for photos that have not been imported into the database based on md5sum of the file
  2) existing - for photos that have already been imported into the database based on md5sum of the file
- Modify the photoimport.py  tool. Have it create two new directories in the specified directory. "new" and "existing".  Recursively descend the specified directory (skipping the new and existing directories). Find all files with a .jpg or .jpeg extension (case insensitive). Process other common image extensions as well. For each file, compute the md5sum of the file. If the md5sum is not found in the database, create a relative softlink to the file in the "new" directory. If the md5sum is found in the database, create a relative softlink to the file in the "existing" directory.
- Every 15 seconds show the progress of discovering and processing of the files. Total the number of new files found and the number of existing files found. Show the rate of files discovered per second and the rate of files processed per second.

### md5sum feature

- Revise the indexer to compute the md5sum of a photo and store it in the database into a column named md5sum. Only update existing records if the md5sum has changed. Use python's hashlib to compute the md5sum.
- Compute the md5sum for new files before insertion into the database.
- Improve the md5sum feature to only update existing records if a "-m/--md5sum" flag is provided. Always compute the md5sum for new files that require insertion into the database.

### tag feature

- Improve the tag feature. On the dashboard page add a "View All Tags" button that links to a page that displays a list of all tags in the database. The page that lists the tags will present the tags in a grid with Tag, Count. The grid should provide column header buttons that allow the user to sort the tags by Tag or Count. Clicking the column will sort by that column in ascending order. Clicking the column again will sort by that column in descending order. The page should also provide a search box that allows the user to search for tags by name. The search should be case-insensitive and should use the LIKE operator to match the search string to the tag name.
- Revise the new tag page. To use a random photo for the background of the page the same as index.html. Also include the same home icon in the top left corner like all the other pages.

### tag entry features

- When the user is entering a tag into the tag textbox, the slideshow should be paused automatically until the user presses enter for the tag or presses the escape key. Pressing enter or escape will resume the slideshow.


### indexer features

- Add memoization feature to _calculate_md5sum() function.
- When indexing photos, use the multiprocessing module to parallelize the indexing process. Use half the number of available CPU cores with a minimum of 1.
- Only get the photo EXIF information if the datetime_taken field is null for a photo.
- The main indexing thread that discovers photo paths should update the log every 15 seconds with the number of photos discovered and the rate of files discovered per second.
- The main indexing thread that updates the database should update the log every 15 seconds with the number of photos processed and the rate of files modified in the database per second.
- While indexing files in the indexer.py collect stats on the files for which the md5sums were computed and exif information was collected
- Revise indexing.py progress log messages to estimate the time left to completion in a human readable format. E.g. 1d8h16m17s . Omit time components that are unnecessary in the estimete. E.g. if there is 5 minutes left there is no need to display the day and hour components.
- ALTER TABLE photos ADD COLUMN metadata_extraction_attempts INTEGER;
- UPDATE photos SET metadata_extraction_attempts = 4 WHERE datetime_taken IS NOT NULL or geolocation IS NOT NULL;
- Do not update or insert photos whose computed square pixels area is less than 10000 square pixels.
- If a photo's record metadate_extraction_attempts field is null or less than three, then extract the photo's EXIF data and update the database with the datetime_taken and geolocation fields.
- When eextracting photo EXIF data increment the database metadata_extraction_attempted field along with the datetime_taken and geolocation fields.
- Add the percentage of files processed to the progress log messages.
- Modify indexer.py to have an "--folder" option that allows the user to specify a folder to index. If the folder is not specified, index the entire PHOTOSHARE_PHOTO_DIR folder.