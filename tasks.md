# Project

A simple lightweight web photosharing app

## Pending Tasks

- Modify the indexer so that it will extract the geolocation and date_time from the photo file and store it in the database. Update existing enteries and insert the information for new photos.
- datetime values are stored to the database as ISO 8601 strings.
- Modify the indexer to record the time new photos are added to the database by setting thedatetime_added field.
- Modify the slideshow to display datetime the photo was taken.
- Modify the slideshow to use javascript to translate geolocation coordingates to an approximate place name if available. Fetch the place name in the background after the photo is displayed. Use the Google Maps API to translate the geolocation to a place name.

## Completed Tasks

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

