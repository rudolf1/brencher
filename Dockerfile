# Use official Python image with uv pre-installed
FROM python:3.11-slim

# Install uv (if not present)
RUN pip install uv

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
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Start the Flask app
CMD ["uv", "pip", "run", "python", "backend/app.py"]
