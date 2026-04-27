#!/bin/bash
set -e

echo "Building Docker image (runtime/base stage)..."
docker build --target base -t calculator-app .

echo "Starting Docker container on port 8080..."
docker run --rm -p 8080:8080 calculator-app
