# Contributing

Thanks for your interest in the 大肥鱼桌宠 (DaFeiYu Desktop Pet) project!

## Development Environment

```powershell
git clone https://github.com/QCYTSN/ds-local-pet.git
cd ds-local-pet
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/validate_assets.py
```

## Before Submitting a PR

- All existing tests must pass
- Asset validation must pass (`tools/validate_assets.py`)
- New code should include appropriate tests
- Ensure no new files from `sprites/` or `assets/references/` are committed

## Adding New Character Actions

1. Create or generate the action master PNG in `assets/processed/masters/`
2. Add an entry in `assets/manifests/actions.json` with proper frame metadata
3. Generate runtime PNGs in `assets/processed/runtime/states/<action_name>/`
4. Update `tools/validate_assets.py` if new validation rules are needed
5. Run `tools/validate_assets.py` to verify

## Adding Local Dialogues

Edit JSON files in `assets/dialogue/`. Each file corresponds to a context category. Follow the existing format for personality variants.

## Code Style

- Target Python 3.11+
- Use `from __future__ import annotations` in all new modules
- Prefer dataclasses and typed protocols over ad-hoc dicts
- Keep imports standard library first, then third-party, then local

## License

By contributing, you agree that your contributions will be licensed under the MIT License (for code) and the terms described in [ASSET_LICENSE.md](ASSET_LICENSE.md) (for assets).