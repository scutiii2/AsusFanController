@echo off
setlocal

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

set "EXE_PATH=%~dp0dist\AsusFanControlUI.exe"

if not exist "%EXE_PATH%" (
    echo Could not find "%EXE_PATH%".
    echo Build it first: pyinstaller build.spec --noconfirm
    pause
    exit /b 1
)

powershell -NoProfile -NonInteractive -Command "$Action = New-ScheduledTaskAction -Execute '%EXE_PATH%'; $Trigger = New-ScheduledTaskTrigger -AtLogOn; $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest; Register-ScheduledTask -TaskName '_ZAsusFanController' -Action $Action -Trigger $Trigger -Principal $Principal -Description 'Launches ASUS Fan Controller, already elevated, at logon.' -Force | Out-Null"

if %ERRORLEVEL% NEQ 0 (
    echo Failed to create the startup task.
    pause
    exit /b 1
)

echo.
echo Done. "_ZAsusFanController" will now launch automatically (already elevated) at logon.
pause
