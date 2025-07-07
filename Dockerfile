# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and sample photos
COPY ./app /app
COPY ./sample_photos /app/sample_photos

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables
ENV PHOTOSHARE_API_KEY="your_api_key"
ENV PHOTOSHARE_PHOTO_DIRS="/app/sample_photos"

# Run main.py when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]