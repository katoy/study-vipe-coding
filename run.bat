@echo off
echo Building Docker image (runtime/base stage)...
docker build --target base -t calculator-app .
if %errorlevel% neq 0 (
    echo Failed to build Docker image.
    pause
    exit /b %errorlevel%
)

echo Starting Docker container on port 8080...
docker run --rm -p 8080:8080 calculator-app
pause
