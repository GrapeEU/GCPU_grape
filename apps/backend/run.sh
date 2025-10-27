#!/bin/bash
# Simple script to run backend without annoying warnings

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run WITHOUT reload to avoid warnings loop
# Just restart manually when you change code
uv run uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000
