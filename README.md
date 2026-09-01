# ASUS Fan Controller

A NitroSense-style desktop app for controlling fan speeds on ASUS laptops:
live temp/RPM gauges, built-in and custom presets, a software fan curve
("Automatic (Override)"), and a system tray.

Built on top of [Karmel0x/AsusFanControl](https://github.com/Karmel0x/AsusFanControl) —
this project wraps its `AsusFanControl.exe` CLI (and the `AsusWinIO64.dll` /
`PsExec.exe` it depends on) with this UI, elevation flow, presets, and curve
logic. Those binaries are bundled as-is in [`src/asusfancontrol/assets`](src/asusfancontrol/assets);
none of that project's code was modified.

## Requirements

- Windows (uses `PsExec`, Task Scheduler, and UAC — Windows-only by design)
- Python 3.11+ to run from source or build the `.exe`

## Features

- Live CPU temp + per-fan RPM/% gauges, with a rolling history graph
- **Automatic (Default)** — hands control back to the motherboard's EC
- **Automatic (Override)** — a draggable temp→speed curve you define, applied
  with a minimum floor and hysteresis to avoid audible fan-speed hunting
- Built-in presets (Silent/Balanced/Performance/Turbo) plus your own,
  saved/deleted from the sidebar
- Minimizes to the system tray instead of quitting; polling and any active
  curve keep running in the background
- Optional "Start with Windows" (see below)

## Running from source

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run.py
```

The app self-elevates on launch (UAC, then `PsExec -s` to reach SYSTEM —
required for the fan driver to actually respond; see
[`elevation.py`](src/asusfancontrol/elevation.py)), so expect a UAC prompt.

For UI development without hardware access, skip elevation:

```bash
set ASUSFANCONTROL_SKIP_ELEVATION=1
.venv\Scripts\python run.py
```

Fan reads/writes will fail without SYSTEM privilege in this mode, but the UI
is fully usable for layout/style work.

## Running the tests

```bash
.venv\Scripts\python -m pytest
```

## Building the standalone .exe

```bash
.venv\Scripts\pyinstaller build.spec --noconfirm
```

Produces `dist/AsusFanControlUI.exe` — a single-file, windowed, self-elevating
executable with the CLI/driver/PsExec assets and the app icon embedded.

## Running this at Windows startup

The easiest way: open the app, go to **Settings** in the sidebar, and check
**Start with Windows**.

This does *not* use a Startup-folder shortcut or a registry Run key — those
would trigger a fresh UAC prompt every single login, since this app
self-elevates on launch. Instead it registers a **Task Scheduler** task named
`_ZAsusFanController`, set to run at logon with the highest privileges, so it
launches already elevated with no prompt. See
[`autostart.py`](src/asusfancontrol/autostart.py).

You can also add or remove that task without opening the app at all, using
[`add_startup_task.bat`](add_startup_task.bat) / [`remove_startup_task.bat`](remove_startup_task.bat)
(both prompt for elevation, then register/unregister the same
`_ZAsusFanController` task — `add_startup_task.bat` expects the exe to
already be built at `dist\AsusFanControlUI.exe`).

Or do it manually, from an elevated PowerShell prompt (this is what the app
and the .bat files actually run — `schtasks /Create` has no way to set a
description, so this uses the `ScheduledTasks` module instead):

```powershell
# register
# (use the actual logged-on user here, not $env:USERNAME — if this is run
# from a SYSTEM-elevated context, as the app itself does, $env:USERNAME
# won't resolve to a valid account and Register-ScheduledTask will fail
# with "No mapping between account names and security IDs was done")
$UserName = (Get-CimInstance -ClassName Win32_ComputerSystem).UserName
$Action = New-ScheduledTaskAction -Execute "C:\path\to\AsusFanControlUI.exe"
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId $UserName -RunLevel Highest
Register-ScheduledTask -TaskName "_ZAsusFanController" -Action $Action -Trigger $Trigger `
  -Principal $Principal -Description "Launches ASUS Fan Controller, already elevated, at logon." -Force

# check it's there
Get-ScheduledTask -TaskName "_ZAsusFanController"

# remove it
Unregister-ScheduledTask -TaskName "_ZAsusFanController" -Confirm:$false
```

## Project layout

```
src/asusfancontrol/
  assets/          bundled AsusFanControl.exe, AsusWinIO64.dll, PsExec.exe, icon
  ui/              PySide6 widgets (sidebar, gauges, graph, curve editor, tray, splash)
  fan_control.py   the only module that shells out to AsusFanControl.exe
  worker.py        background thread that owns all fan I/O, so the UI never blocks
  app_controller.py  mode/preset/curve state, wired to the UI via Qt signals
  elevation.py     UAC -> SYSTEM self-elevation, mirroring the original FanController.bat
  autostart.py     Task Scheduler registration for "Start with Windows"
  config.py        JSON persistence (%APPDATA%\AsusFanControlUI\config.json)
tests/             unit tests for curve math, config persistence, CLI-output parsing
docs/superpowers/specs/  design notes from planning this project
add_startup_task.bat     registers the _ZAsusFanController startup task
remove_startup_task.bat  removes it
```
