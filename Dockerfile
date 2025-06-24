# Dockerfile (place this in your project root: /Users/abubakraqeel/dev/check24/Dockerfile)

# ---- Stage 1: Build React Frontend ----
FROM node:22-alpine AS frontend-builder

# Set working directory for frontend
WORKDIR /app/frontend

# Copy frontend package.json and package-lock.json (or yarn.lock)
COPY frontend/package.json frontend/package-lock.json* ./
# If using yarn, copy yarn.lock instead of package-lock.json

# Install frontend dependencies
RUN npm install
# If using yarn: RUN yarn install --frozen-lockfile

# Copy the rest of the frontend source code
COPY frontend/ ./

# Build the React app
RUN npm run build
# If using yarn: RUN yarn build

# ---- Stage 2: Setup Python Backend and Serve ----
FROM python:3.12.2-slim AS backend-runner
# Use a Python version that matches your local development (e.g., 3.9, 3.10, 3.11, 3.12)
# python:3.12-slim is a good lightweight choice

# Set environment variables (can also be set in Railway UI)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=application.py
ENV FLASK_ENV=production
# PORT will be provided by Railway, usually 8080 or similar for the container,
# Gunicorn will bind to this. Railway then maps its external port to this.

# Set working directory for the backend
WORKDIR /app

# Install system dependencies that might be needed by Python packages (e.g., for lxml)
# For -slim images, you might need to install build tools first if any Python package compiles C extensions.
# Example: RUN apt-get update && apt-get install -y --no-install-recommends gcc libxml2-dev libxslt1-dev && rm -rf /var/lib/apt/lists/*
# Add more as needed based on your requirements.txt. For now, let's try without.

# Copy requirements.txt first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# Create and use a virtual environment (good practice even in Docker for consistency)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn # Add gunicorn for production WSGI server

# Copy the entire application code (backend 'app' folder, application.py, etc.)
COPY . .
# This copies everything from your project root in your local machine to /app in the container.
# This includes the 'frontend' directory, but we'll use the built assets from the previous stage.

# Copy built frontend assets from the frontend-builder stage
# This will place your React build output into /app/frontend/build inside the container
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Expose the port Gunicorn will run on (Railway will map this)
# Gunicorn will listen on the $PORT environment variable set by Railway, or 8000 by default if not set
# We will use the $PORT variable given by Railway in the CMD
# EXPOSE 8000 # This is more for documentation; Railway handles actual port mapping

# Command to run the application using Gunicorn
# Railway will set the PORT environment variable. Gunicorn will bind to 0.0.0.0:$PORT
# Ensure application:application points to your Flask app object (application.py file, application variable)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "application:application"]