@echo off
setlocal

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

powershell -NoProfile -NonInteractive -Command "if (Get-ScheduledTask -TaskName '_ZAsusFanController' -ErrorAction SilentlyContinue) { Unregister-ScheduledTask -TaskName '_ZAsusFanController' -Confirm:$false; Write-Host 'Removed.' } else { Write-Host 'No _ZAsusFanController startup task found - nothing to remove.' }"

pause
