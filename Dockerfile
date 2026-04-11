# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY openapi.yaml /app/openapi.yaml
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
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

# Copy backend
COPY backend/ ./backend/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port for the web server
EXPOSE 5001

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Start the app with uvicorn
CMD ["python3", "backend/app.py"]
