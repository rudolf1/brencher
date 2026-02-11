# Use official Python image with uv pre-installed
FROM python:3.12.3-alpine

# Install uv (if not present)
RUN pip install uv
# Install git
RUN apk update && apk upgrade
RUN apk add --no-cache git docker-cli
# Set workdir
WORKDIR /app

# Copy requirements and install dependencies with uv
COPY requirements.txt ./
RUN uv venv .venv && \
    uv pip install -r requirements.txt

# Copy backend and frontend
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Expose port for Flask
EXPOSE 5001

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Start the Flask app
CMD ["python3", "backend/app.py"]
