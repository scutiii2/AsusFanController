#requires -version 5
# Build AsusFanControlUI.exe with a pinned status header (progress %) and
# scrolling logs below it.
# Usage: build.ps1 [-SkipTests]
param([switch]$SkipTests)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$VenvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$ExeName = "AsusFanControlUI.exe"
$esc = [char]27
$HeaderRows = 3

# How many steps will actually run, so the percentage is honest.
$script:StepTotal = 2                                   # install + build
if (-not $SkipTests) { $script:StepTotal++ }
if (-not (Test-Path $VenvPy)) { $script:StepTotal++ }   # create venv
$script:StepIndex = 0

# Enable ANSI/VT so the scroll-region escapes work. If the console can't
# (redirected output, old host), fall back to plain lines.
$fancy = $false
try {
    Add-Type -Namespace VT -Name Native -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError=true)]
public static extern System.IntPtr GetStdHandle(int nStdHandle);
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError=true)]
public static extern bool GetConsoleMode(System.IntPtr h, out uint mode);
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError=true)]
public static extern bool SetConsoleMode(System.IntPtr h, uint mode);
'@ -ErrorAction Stop
    $h = [VT.Native]::GetStdHandle(-11)
    $mode = 0
    if ([VT.Native]::GetConsoleMode($h, [ref]$mode)) {
        [void][VT.Native]::SetConsoleMode($h, $mode -bor 0x0004)
        $null = [Console]::WindowHeight
        $fancy = $true
    }
} catch { $fancy = $false }

function Set-Header([int]$pct, [string]$label) {
    $pct = [Math]::Max(0, [Math]::Min(100, $pct))
    if ($fancy) {
        $w = [Console]::WindowWidth
        $barCells = 24
        $filled = [int][Math]::Round($barCells * $pct / 100)
        $bar = ('#' * $filled) + ('-' * ($barCells - $filled))
        $line = "  [$bar] {0,3}%  {1}" -f $pct, $label
        if ($line.Length -gt $w) { $line = $line.Substring(0, $w) }
        # Save cursor, jump to row 2, clear it, write, restore cursor.
        [Console]::Write("$esc[s$esc[2;1H$esc[2K$line$esc[u")
    } else {
        Write-Host ("[{0,3}%] {1}" -f $pct, $label) -ForegroundColor Cyan
    }
}

function Initialize-Screen {
    if (-not $fancy) { return }
    $w = [Console]::WindowWidth
    $bottom = [Console]::WindowHeight
    [Console]::Write("$esc[2J$esc[H")
    [Console]::Write("$esc[1;1H$esc[7m  Building $ExeName $(' ' * [Math]::Max(0, $w - 13 - $ExeName.Length))$esc[0m")
    [Console]::Write("$esc[3;1H$('-' * $w)")
    [Console]::Write("$esc[$($HeaderRows + 1);$($bottom)r")   # DECSTBM scroll region
    [Console]::Write("$esc[$($HeaderRows + 1);1H")            # cursor into the log area
    Set-Header 0 "starting..."
}

function Reset-Screen {
    if ($fancy) { [Console]::Write("$esc[r`n") }             # release scroll region
}

function Invoke-Step([string]$label, [scriptblock]$action) {
    # Percentage reflects steps completed before this one; the last step ends
    # at 100% via the final Set-Header.
    $pct = [int](100 * $script:StepIndex / $script:StepTotal)
    $script:StepIndex++
    Set-Header $pct $label
    Write-Host ""
    Write-Host "=== $label ===" -ForegroundColor DarkCyan
    & $action
}

function Stop-WithError([string]$message) {
    Reset-Screen
    Set-Header $([int](100 * $script:StepIndex / $script:StepTotal)) "FAILED"
    Write-Host ""
    Write-Host $message -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

try {
    Initialize-Screen

    if (-not (Test-Path $VenvPy)) {
        Invoke-Step "Creating virtual environment (.venv)" {
            & python -m venv .venv
            if ($LASTEXITCODE -ne 0) { Stop-WithError "Could not create .venv (is Python on PATH?)." }
        }
    }

    Invoke-Step "Installing dependencies" {
        & $VenvPy -m pip install --disable-pip-version-check -r requirements.txt
        if ($LASTEXITCODE -ne 0) { Stop-WithError "pip install failed." }
    }

    # PyInstaller can't overwrite a running exe, and the app runs as SYSTEM so
    # this script can't close it.
    if (Get-Process -Name ($ExeName -replace '\.exe$','') -ErrorAction SilentlyContinue) {
        Stop-WithError "$ExeName is running. Quit it from the tray icon, then run this again."
    }

    if (-not $SkipTests) {
        Invoke-Step "Running tests" {
            & $VenvPy -m pytest -q
            if ($LASTEXITCODE -ne 0) { Stop-WithError "Tests failed; build stopped." }
        }
    }

    Invoke-Step "Building $ExeName" {
        & $VenvPy -m PyInstaller build.spec --noconfirm
        if ($LASTEXITCODE -ne 0) { Stop-WithError "PyInstaller failed." }
    }

    Reset-Screen
    Set-Header 100 "Done"
    Write-Host ""
    Write-Host "Done: $(Join-Path $PSScriptRoot 'dist\')$ExeName" -ForegroundColor Green
    Read-Host "Press Enter to close"
}
catch {
    Stop-WithError $_.Exception.Message
}
