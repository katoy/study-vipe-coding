@echo off
echo Building Docker image...
docker build -t calculator-app .
if %errorlevel% neq 0 (
    echo Failed to build Docker image.
    pause
    exit /b %errorlevel%
)

echo Starting Docker container on port 8000...
docker run --rm -p 8000:8000 calculator-app
pause
