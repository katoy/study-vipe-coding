#!/bin/bash
set -e

echo "Building CI image (ci stage)..."
docker build --target ci -t calculator-ci:ci .

echo "Running CI checks inside container..."
docker run --rm calculator-ci:ci
