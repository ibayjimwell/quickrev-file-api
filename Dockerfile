# Dockerfile
# 1. Use an official Python base image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file into the container
COPY requirements.txt .

# 4. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container
# Assumes your FastAPI main file is named main.py and is in the root.
# Adjust this path if your code is in a subdirectory (e.g., 'src/.')
COPY . .

# 6. Define the port the container will listen on
# Cloud Run injects the PORT environment variable; Uvicorn must listen on it.
ENV PORT 8080

# 7. Define the command to run your FastAPI application using Uvicorn
# Replace 'main:app' with the correct module:ASGI_instance if your file/variable is different.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]