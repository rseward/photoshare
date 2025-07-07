# PhotoShare

A simple photo sharing web service which aims to be compatible with unsplash JS clients.

This project was/is a collaboration between gemini-cli and myself. Gemini-cli and I have spent approximately 4 man-hours (my time) on the project so far. This has been a project I have wanted to implement for some time. I have a magic-mirror on my desk with plugins to pull images from unsplash. My goal is to alter that plugin to pull images from my photo collection instead of unsplash using this application.


## Running the application

    - `PHOTOSHARE_PHOTO_DIRS`: A comma-separated list of directories to scan for photos.
    - `PHOTOSHARE_PHOTO_IGNORE_PATS`: (Optional) The absolute path to a file containing newline-separated glob patterns of photos to ignore during indexing.

### With Docker

1.  **Build the Docker image:**

    ```bash
    docker build -t photoshare .
    ```

2.  **Run the Docker container with sample photos:**

    ```bash
    docker run -p 8000:8000 -e PHOTOSHARE_API_KEY="your_api_key" photoshare
    ```

    Replace `"your_api_key"` with your desired API key. The sample photos are included in the container.

3.  **Run the Docker container with your own photos:**

    ```bash
    docker run -p 8000:8000 \
        -e PHOTOSHARE_API_KEY="your_api_key" \
        -e PHOTOSHARE_PHOTO_DIRS="/path/to/your/photos" \
        -v /path/to/your/photos:/path/to/your/photos \
        photoshare
    ```

    Replace `"your_api_key"` with your desired API key and `"/path/to/your/photos"` with the actual path to your photo directory on the host machine.

### Locally

1.  **Install dependencies:**

    ```bash
    uv pip install -r requirements.txt
    ```

2.  **Set environment variables:**

    ```bash
    export PHOTOSHARE_API_KEY="your_api_key"
    export PHOTOSHARE_PHOTO_DIRS="./sample_photos"
    ```

3.  **Run the application:**

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

## Standalone Indexer

For large photo collections, it is recommended to run the indexing process separately from the web service. This can be done using the `indexer.py` script.

1.  **Set the environment variables** as you would for the web service.
2.  **Run the indexer:**

    ```bash
    python indexer.py index
    ```

This will scan the directories and populate the database. It creates an `index.lock` file in the same directory as the database, which prevents the web service from starting its own indexing thread. The lock file is removed automatically when indexing is complete.

## Testing

To run the unit tests, simply run `pytest`:

```bash
pytest
```

The tests will automatically use the `sample_photos` directory.

## Usage

1.  Open your web browser and navigate to `http://localhost:8000`.
2.  Enter your API key in the input field.
3.  Click the "Get Random Photo" button to view a random photo.

