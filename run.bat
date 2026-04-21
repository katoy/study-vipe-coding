@echo off
REM Activate venv if exists
IF EXIST .venv\Scripts\activate (
    call .venv\Scripts\activate
)
uvicorn app:app --reload --host 0.0.0.0 --port 8000
