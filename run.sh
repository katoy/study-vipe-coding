#!/bin/bash
set -e

echo "Building Docker image..."
docker build -t calculator-app .

echo "Starting Docker container on port 8000..."
docker run --rm -p 8000:8000 calculator-app
