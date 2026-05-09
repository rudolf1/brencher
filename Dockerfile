# Use official Python image with uv pre-installed
FROM python:3.12.3-slim AS typecheck

# Install uv (if not present)
RUN pip install uv

# Set workdir
WORKDIR /app

# Install development dependencies and run mypy before the runtime image is built.
COPY requirements.txt requirements-dev.txt mypy.ini ./

RUN uv venv .venv && \
    uv pip install -r requirements-dev.txt

COPY backend/ ./backend/
COPY tests/ ./tests/

RUN . .venv/bin/activate && \
    mypy --no-incremental --config-file mypy.ini backend tests && \
    touch /tmp/typecheck.done

# Use official Python image with uv pre-installed
FROM python:3.12.3-alpine AS base

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

# Expose port for the web server
EXPOSE 5001

# Ensure the mypy pre-build stage is executed.
COPY --from=typecheck /tmp/typecheck.done /tmp/typecheck.done

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Start the app with uvicorn
CMD ["python3", "backend/app.py"]
