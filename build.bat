@echo off
rem Thin launcher for build.ps1 (pinned status header + scrolling logs).
rem Usage: build.bat [--skip-tests]
setlocal
set "PS_ARGS="
if /I "%~1"=="--skip-tests" set "PS_ARGS=-SkipTests"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %PS_ARGS%
exit /b %ERRORLEVEL%
