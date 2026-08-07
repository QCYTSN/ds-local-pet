# v0.1.0 — First Public Release

**2026-08-07**

The first public release of 大肥鱼桌宠 (DaFeiYu Desktop Pet), a lightweight, offline-first desktop companion for Windows.

## Highlights

- **4-frame side-walking animation** with left/right directional mirroring
- **13 character states**: idle, thinking, walking, happy, talking, angry, poke-react, eating, sweeping, sleeping, dragging, falling, dizzy
- **Mouse interactions**: head-pat, poke, drag-and-throw, double-click feed
- **Local personality dialogue system**: 4 personalities (standard, tsundere, gentle, meme) with context-aware responses
- **Optional local environment awareness**: reads foreground window metadata only — no screenshots, no screen recording, no network upload
- **Privacy-first design**: sensitive apps (password managers, banking, remote desktop, incognito windows) are never tracked
- **Windows single-instance and system tray**: second launch activates existing pet, tray icon for quick control
- **Compact right-click panel**: quick actions (feed, say, happy, rest) + expandable settings (size, mode, awareness, topmost, autostart, passthrough)

## Known Limitations

- **Windows only**: no macOS or Linux support at this time
- **PyInstaller onedir bundle**: ~200 MB on disk due to PySide6 runtime; a onefile version would be smaller but slower to start
- **No automatic update mechanism**: users must manually download new releases
- **No energy/rest system polish**: the pet state system is functional but not yet reflected in proactive behavior
- **No multi-monitor DPI awareness**: may appear too small or too large on non-100% scaling displays
- **No sound effects**: entirely visual
- **No network features**: the pet does not connect to the internet; all dialogue is local
- **Config file location**: `config.json` and `pet_state.json` are written next to the executable (or project root when running from source)

## Downloads

- **Windows (x64)**: `DS-Local-Pet-v0.1.0-win-x64.zip` — download, extract, and run `DS-Local-Pet-v0.1.0-win-x64.exe`

## Credits

See [CREDITS.md](../CREDITS.md) and [ASSET_LICENSE.md](../ASSET_LICENSE.md) for licensing details.