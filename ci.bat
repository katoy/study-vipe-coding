@echo off
echo Building CI image (ci stage)...
docker build --target ci -t calculator-ci:ci .
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
echo Running CI checks inside container...
docker run --rm calculator-ci:ci
exit /b %ERRORLEVEL%
