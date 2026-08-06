@echo off
setlocal
cd /d "%~dp0"
set "PET_ENTRY=%CD%\main.py"

if exist "%CD%\.venv\Scripts\pythonw.exe" (
    start "" "%CD%\.venv\Scripts\pythonw.exe" "%PET_ENTRY%"
) else (
    start "" pythonw "%PET_ENTRY%"
)

endlocal
