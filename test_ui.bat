@echo off
echo Starting Playwright E2E tests in Docker...
echo This will use the official Playwright Linux image to avoid local environment issues.
echo.

docker run --rm -v "%cd%:/app" -w /app mcr.microsoft.com/playwright/python:v1.43.0-jammy bash -c "pip install uv && uv sync && uv run pytest -o addopts='' tests/test_ui.py"

if %errorlevel% neq 0 (
    echo.
    echo Tests failed or container encountered an error.
    pause
    exit /b %errorlevel%
)

echo.
echo Tests completed successfully!
pause
