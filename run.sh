#!/bin/bash
set -e

echo "Building Docker image (runtime/base stage)..."
docker build --target base -t calculator-app .

echo "Starting Docker container on port 8000..."
docker run --rm -p 8000:8000 calculator-app
