#!/bin/bash
# Script to run integration tests inside Docker container
# This ensures tests don't harm the host environment

set -e

echo "Building test Docker image..."
docker build -t brencher-test -f Dockerfile.test .

echo "Running integration tests in Docker container..."
docker run --rm brencher-test

echo "Tests completed successfully!"
