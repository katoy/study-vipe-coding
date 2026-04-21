#!/bin/bash
# Activate venv if exists
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi
exec uvicorn app:app --reload --host 0.0.0.0 --port 8000
