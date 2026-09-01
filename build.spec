# PyInstaller spec: standalone windowed exe with the AsusFanControl CLI,
# EC driver DLL, and PsExec bundled as data files.
# Build with: pyinstaller build.spec

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("src/asusfancontrol/assets/AsusFanControl.exe", "asusfancontrol/assets"),
        ("src/asusfancontrol/assets/AsusWinIO64.dll", "asusfancontrol/assets"),
        ("src/asusfancontrol/assets/PsExec.exe", "asusfancontrol/assets"),
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
