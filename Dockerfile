# ---- Stage 1: Build React Frontend ----
FROM node:22-alpine AS frontend-builder

# Set working directory for frontend
WORKDIR /app/frontend

# Copy frontend package.json and package-lock.json
COPY frontend/package.json frontend/package-lock.json* ./

# Install frontend dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY frontend/ ./

# Build the React app
RUN npm run build

# ---- Stage 2: Setup Python Backend and Serve ----
FROM python:3.12.2-slim AS backend-runner

# Set environment variables (can also be set in Railway UI)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=application.py
ENV FLASK_ENV=production

# Set working directory for the backend
WORKDIR /app

# Copy requirements.txt first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn # Add gunicorn for production WSGI server

COPY . .

COPY --from=frontend-builder /app/frontend/build ./frontend/build

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "application:application"]