# Project

A simple lightweight web photosharing app

## Pending Tasks

- Add a home icon using app/static/imgs/home-icon-cropped-392x392.png to the top left of the dashboard and slideshow pages. On the slideshow page push the delete button slightly to the right of the home icon. Scale the icon image to 50x50 pixels. The home icon should be a link to the /ui/dashboard url.

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

