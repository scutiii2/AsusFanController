# AsusFanControl UI — Design Spec

Date: 2026-09-01
Status: Approved (pending spec review)

## Goal

Build a NitroSense-style desktop app (dark theme, live gauges, mode presets,
custom fan curve) that controls Asus laptop fans through the existing
`AsusFanControl.exe` CLI tool, replacing the current bare-bones
`AsusFanControlGUI.exe` / `FanController.bat` workflow with something
polished and self-contained.

Scope is fan control only — no GPU mode switching, battery limiter, or other
NitroSense features. The code should be structured so a panel/module could be
added later, but nothing beyond fan control ships in v1.

## Current state (reference, read-only)

`D:\User\Documents\AsusFanControl` contains prebuilt binaries this project
wraps but does not modify:

- `AsusFanControl.exe` — CLI, the actual fan control mechanism:
  - `--get-fan-speeds`, `--set-fan-speeds=0-100` (0 = disable override)
  - `--get-fan-count`
  - `--get-fan-speed=fanId`, `--set-fan-speed=fanId:0-100`
  - `--get-cpu-temp`
- `AsusWinIO64.dll` — raw EC I/O driver the CLI talks to.
- `AsusFanControlGUI.exe` — existing prebuilt GUI (being replaced).
- `PsExec.exe` — Sysinternals tool used to reach SYSTEM privilege.
- `FanController.bat` — current launcher: checks for an admin session: if
  missing, relaunches itself elevated via UAC (`Start-Process ... -Verb
  RunAs`), then uses `PsExec -i -s -d` to relaunch `AsusFanControlGUI.exe`
  as SYSTEM.

Confirmed by running the CLI directly (non-elevated): it returns garbage
(`fan count: -1`, `cpu temp: 0`) without SYSTEM privilege — Administrator
via UAC alone is not enough, matching why the existing launcher does the
two-step UAC → PsExec -s escalation.

## Architecture

Single PySide6 application, packaged to a standalone `.exe` via PyInstaller.
Copies of `AsusFanControl.exe`, `AsusWinIO64.dll`, and `PsExec.exe` are
bundled into this project's assets at build time (copied from the read-only
reference folder once; the reference folder itself is never modified or
depended on at runtime).

**Elevation flow** (mirrors `FanController.bat`):
1. On launch, check for an admin token.
2. If absent, relaunch self elevated via UAC (`Verb RunAs`); the
   non-elevated instance exits.
3. The elevated instance relaunches itself again via `PsExec -s -d` to reach
   SYSTEM; the merely-Administrator instance exits.
4. The final SYSTEM-level process runs the `QApplication` and all fan I/O.

**Fan control wrapper** (`fan_control.py`): the only module that shells out
to `AsusFanControl.exe`. Exposes `get_fan_speeds()`, `get_fan_count()`,
`get_cpu_temp()`, `set_fan_speed(fan_id, pct)`, `set_auto()` (issues
`--set-fan-speeds=0`). All other modules call through this wrapper, never
subprocess directly — keeps CLI-output parsing and error handling in one
place.

## Modes

- **Manual** — per-fan slider (0–100%), applies immediately on change.
- **Preset** — a named set of fixed per-fan % values, applied like Manual.
  Built-in presets: Silent (~30%), Balanced (~50%), Performance (~75%),
  Turbo (100%) — read-only. Users can save the current slider state as a
  new named preset, and rename/delete their own presets.
- **Automatic** — issues `--set-fan-speeds=0`, handing control back to the
  EC's native fan curve. Polling continues (read-only) to keep the live
  gauges/graph updated, but no set commands are issued while this mode is
  active.
- **Automatic (Override)** — one user-editable temp→speed curve
  (draggable breakpoints on a temp/speed graph), shared across all detected
  fans (laptop CPU/GPU fans are assumed correlated enough that per-fan
  curves aren't needed). A background poll loop (default interval,
  user-adjustable) reads CPU temp, interpolates the target % from the
  curve, and applies:
  - a minimum floor (e.g. 20%) — fans never go fully off while this mode
    is active;
  - hysteresis — a new set command is only issued if the target differs
    from the last-applied value by more than a threshold, and a downward
    change must be sustained across two consecutive polls before being
    applied — to prevent audible fan-speed hunting near curve breakpoints.

Switching away from any mode (to Manual, another Preset, or Automatic)
immediately stops that mode's background behavior (e.g. leaving Automatic
(Override) stops the curve poll loop from issuing further set commands).

## UI

NitroSense-inspired dark theme. Sidebar (a single "Fan Control" section for
v1, but structured so more sections could be added without a rewrite) plus
main content:

- Live gauges: CPU temp, per-fan RPM and %.
- Pill-style mode selector: Silent / Balanced / Performance / Turbo / any
  user presets / Custom / Automatic.
- Real-time line graph (pyqtgraph) of recent temp and fan speed history.
- Curve editor panel, visible only while Automatic (Override) is selected.
- Preset manager: save-current-as-preset, rename/delete custom presets.
- Settings panel: "Start with Windows" toggle, poll interval.

**System tray**: closing the main window minimizes to tray instead of
quitting — polling and any active curve logic keep running in the
background. Tray icon: left-click restores the window; right-click menu
offers quick mode switching and Quit (a real exit).

**Start with Windows**: implemented as a Task Scheduler entry ("run at
logon, highest privileges") created/removed when the settings toggle is
changed — not a registry Run key, since a Run key would trigger a fresh
UAC prompt on every login (the app self-elevates on launch); a scheduled
task with highest privileges launches already-elevated with no prompt.

## Persistence

`%APPDATA%\AsusFanControlUI\config.json` stores: user-created presets,
custom curve breakpoints, last active mode, poll interval, and the
start-with-Windows toggle state. Loaded on startup; written whenever
settings, presets, or the curve change.

## Error handling

Failures surface as a dialog showing the real underlying error (stderr /
exit code), never a silent failure:
- `AsusFanControl.exe` or `AsusWinIO64.dll` missing/corrupted from the
  bundled assets.
- `PsExec.exe` blocked (common with AV/SmartScreen flagging Sysinternals
  tools) — dialog explains this specifically, with a retry option.
- UAC prompt declined by the user — explanation dialog, then graceful exit
  (no silent retry loop).

## Testing

Hardware interaction (actual fan speed changes, real temp readings) can
only be verified manually on the real laptop — no automated coverage
possible there. Unit-testable in isolation:
- Curve interpolation and hysteresis/floor logic.
- Config load/save (JSON round-trip, defaults on missing/corrupt file).
- `fan_control.py`'s CLI-output parsing (given known stdout strings from
  the documented `AsusFanControl.exe` output formats).

## Out of scope (v1)

- GPU mode switching, battery charge limiter, macro keys, or any other
  NitroSense feature beyond fan control.
- Per-fan custom curves (a single shared curve is used for all fans).
- Any modification to the read-only `AsusFanControl` reference folder.
