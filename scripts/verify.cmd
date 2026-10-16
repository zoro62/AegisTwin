@echo off
cd /d "%~dp0\.."
.venv\Scripts\python.exe -m pip check
if errorlevel 1 exit /b 1
.venv\Scripts\ruff.exe check backend tests scripts migrations lab
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m scripts.evaluate
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m scripts.benchmark
if errorlevel 1 exit /b 1
cd frontend
call npm run build
if errorlevel 1 exit /b 1
