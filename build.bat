@echo off
setlocal
cd /d "%~dp0"

rem Usage: build.bat [--skip-tests]

set "VENV_PY=.venv\Scripts\python.exe"
set "EXE_NAME=AsusFanControlUI.exe"

if not exist "%VENV_PY%" (
    echo Creating virtual environment in .venv ...
    python -m venv .venv || goto :fail
)

echo Installing/updating dependencies ...
"%VENV_PY%" -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto :fail

rem PyInstaller can't overwrite the exe while the app is running (it runs as
rem SYSTEM, so this script can't close it either).
tasklist /FI "IMAGENAME eq %EXE_NAME%" 2>nul | find /I "%EXE_NAME%" >nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo %EXE_NAME% is running. Quit it from the tray icon, then run this again.
    goto :fail
)

if /I not "%~1"=="--skip-tests" (
    echo Running tests ...
    "%VENV_PY%" -m pytest -q || goto :fail
)

echo Building %EXE_NAME% ...
"%VENV_PY%" -m PyInstaller build.spec --noconfirm || goto :fail

echo.
echo Done: %~dp0dist\%EXE_NAME%
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
