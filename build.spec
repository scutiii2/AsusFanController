# PyInstaller spec: standalone windowed exe with the app icon bundled as a
# data file. The EC driver DLL is not bundled (see below).
# Build with: pyinstaller build.spec

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        # AsusWinIO64.dll is not bundled (ASUS-owned); it is copied from the
        # driver store at startup by fan_control.ensure_driver_library().
        ("src/asusfancontrol/assets/fan.png", "asusfancontrol/assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AsusFanControlUI",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="src/asusfancontrol/assets/fan.ico",
)
