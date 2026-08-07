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
        ├── *.dll, *.pyd, base_library.zip, PySide6/  (PyInstaller runtime)
        ├── icon.ico
        ├── sprites/
        │   └── icon.png                  (tray icon)
        └── assets/
            ├── manifests/actions.json    (the only runtime manifest)
            ├── dialogue/*.json
            ├── app_categories.json
            ├── privacy_rules.json
            └── processed/runtime/states/ (runtime character frames)
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

## Packaging Policy: Whitelist Only

The release contains **only what the running application actually reads**.
`tools/build_release.py` copies an explicit whitelist
(`RUNTIME_ASSET_DIRS` / `RUNTIME_ASSET_FILES`); it never copies a whole
directory and then tries to delete parts of it afterwards.

## What Gets Bundled

| Path | Read by |
|------|---------|
| Python code + dependencies | PyInstaller |
| `assets/manifests/actions.json` | `animation.asset_registry.AssetRegistry` |
| `assets/processed/runtime/states/` | animation frame loading |
| `assets/dialogue/*.json` | `dialogue.local_rules.DialogueManager` |
| `assets/app_categories.json` | `behavior.classifier.AppClassifier` |
| `assets/privacy_rules.json` | `awareness` privacy policy |
| `sprites/icon.png` | `pet.window._create_tray` (system tray icon) |
| `icon.ico` | shortcut / window icon |

`actions.json` is the only manifest shipped. `character_spec.json`,
`runtime_inventory.json`, `source_inventory.json`, `extraction_report.json`
and `state_extraction_report.json` are development records and are not read
at runtime.

## What Does NOT Get Bundled

- Source sprites other than `sprites/icon.png` (paid / third-party reference art)
- Reference assets (`assets/references/`, `assets/source/`)
- Candidate/development assets (`assets/candidates/`)
- Master processing files (`assets/processed/masters/`)
- Development manifests and extraction reports
- Preview material (`assets/previews/`) — documentation only, never loaded at runtime
- Test files, development tools, venv and build artifacts
- User config files (`config.json`, `pet_state.json`)

## Verification

The build **fails and produces no zip** if any of these checks fail:

1. `DS-Local-Pet-v{VERSION}-win-x64.exe` and root `icon.ico` exist
2. `assets/manifests/actions.json`, `assets/app_categories.json`,
   `assets/privacy_rules.json`, `sprites/icon.png` exist
3. All nine dialogue JSON files exist
4. PyInstaller runtime is complete (`python3*.dll`, `base_library.zip`, `PySide6/`)
5. **Every frame path referenced by `actions.json` resolves inside the bundle**
6. No forbidden content (dev manifests, references, source, candidates,
   masters, tests, tools, `__pycache__`, user config, non-runtime sprites)
7. No developer absolute path (project root, user home, `C:\Users\...`,
   `D:\Github_Ku\...`) appears in any shipped text file
8. The finished zip is re-checked against the same forbidden-content rules

A missing optional extra (currently `_internal/icon.ico`) only prints a warning.

Manual verification steps:

1. Double-click the exe — should start without errors
2. Right-click the pet — control panel should open
3. Click the tray icon — should toggle visibility
4. Launch the exe again — should activate the existing instance (single-instance check)
5. Verify animations play correctly (walk, idle, happy, etc.)