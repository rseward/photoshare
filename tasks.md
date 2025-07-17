# Project

A simple lightweight web photosharing app

## Pending Tasks

- Refactor the main landing index.html page. Move it's URL to /ui/slideshow
- When the root URL / is accessed redirect the browser to the new /ui/slideshow URL.
- Provide a slideshow page identical to the main /ui/slideshow/ URL that displays random photos that have been tagged with a specified tag.
  The URL to access this mode will be /ui/slideshow/{tag}

## Completed Tasks

- Load and display any tags created for a photo when displaying the photo on the index.html page
- Create a /photos/bytag/{tag} end point. Randomly select a photo with that tag to send to the calling entity. E.g. this endpoint is used to create a slideshow of random photos matching that tag.

