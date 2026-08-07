# Release Build

## Build Command

```powershell
.\.venv\Scripts\python.exe tools\build_release.py
```

This produces:

```
dist/
├── DS-Local-Pet-v0.1.0-win-x64.zip
└── DS-Local-Pet-v0.1.0-win-x64/
    ├── DS-Local-Pet-v0.1.0-win-x64.exe
    ├── icon.ico
    └── _internal/
        ├── *.dll, *.pyd  (PyInstaller runtime)
        ├── assets/
        │   ├── manifests/
        │   ├── dialogue/
        │   ├── processed/runtime/
        │   └── ...
        └── ...
```

## Build Tool: PyInstaller

[PyInstaller](https://pyinstaller.org/) bundles the Python interpreter and all dependencies into a self-contained directory.

## Onedir vs Onefile

| Aspect | Onefile | Onedir (chosen) |
|--------|---------|-----------------|
| User experience | Single .exe | Folder with .exe + _internal |
| Startup time | Slow (extract to temp) | Instant |
| Antivirus false positives | Higher | Lower |
| Resource path handling | Complex (sys._MEIPASS) | Straightforward |
| Debugging | Hard | Easy (inspect files) |
| Distribution | One file | Compressed zip |

**Why onedir is better for this project:**

- PySide6 is ~200 MB on disk; onefile extraction takes several seconds on every launch
- Antivirus software frequently flags PyInstaller onefile executables as suspicious
- Resource paths in onedir follow the same layout as the source tree, making it easier to verify
- Users can inspect the bundle contents if something goes wrong

## Requirements

- Python 3.11+
- Windows x64
- Dependencies installed via `pip install -r requirements.txt`
- PyInstaller (auto-installed by the build script)

## Version

The version is read from `app/version.py` (`__version__ = "0.1.0"`). No manual duplication.

## What Gets Bundled

- All Python code and dependencies
- Runtime character assets (`assets/processed/runtime/`)
- Action manifests (`assets/manifests/`)
- Dialogue files (`assets/dialogue/`)
- App categories and privacy rules (`assets/app_categories.json`, `assets/privacy_rules.json`)
- Icon

## What Does NOT Get Bundled

- Source sprites (`sprites/`)
- Reference assets (`assets/references/`, `assets/source/`)
- Candidate/development assets (`assets/candidates/`)
- Master processing files (`assets/processed/masters/`)
- Test files
- Development tools
- Venv and build artifacts
- User config files

## Verification

After building, the script automatically checks:

- `DS-Local-Pet-v{VERSION}-win-x64.exe` exists
- `assets/manifests/actions.json` is present
- `assets/dialogue/` directory is present
- `assets/processed/runtime/states/` directory is present

Manual verification steps:

1. Double-click the exe — should start without errors
2. Right-click the pet — control panel should open
3. Click the tray icon — should toggle visibility
4. Launch the exe again — should activate the existing instance (single-instance check)
5. Verify animations play correctly (walk, idle, happy, etc.)