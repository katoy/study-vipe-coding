#!/usr/bin/env bash
set -euo pipefail

# Run tests with coverage and update README
PYTHON=${PYTHON:-python}
$PYTHON -m pytest --maxfail=1 -q --disable-warnings --cov=app --cov-report=xml:coverage.xml
$PYTHON scripts/update_readme_coverage.py coverage.xml README.md

echo "Coverage measured and README updated." 
