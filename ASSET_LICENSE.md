# Asset License & Copyright

## Source Code

The source code in this repository is licensed under the **MIT License** (see [LICENSE](LICENSE)), unless otherwise stated in individual files.

The MIT License applies to:
- All `.py` files in `app/`, `animation/`, `pet/`, `awareness/`, `behavior/`, `dialogue/`, `settings/`, `tools/`, `tests/`
- `main.py`, `桌宠.py`, `preprocess.py`, `preprocess2.py`, `make_zip.py`
- Build scripts, CI configuration, and documentation

## Upstream Code

This project is based on the MIT-licensed [1190fasheqi/dafeiyu-pet](https://github.com/1190fasheqi/dafeiyu-pet). The original MIT license is preserved in [LICENSE](LICENSE), and full attribution is in [CREDITS.md](CREDITS.md).

## Visual Character Assets

**Visual character assets are governed separately from the MIT code license.**

### Runtime Assets (MIT Licensed)

The following files in `assets/processed/runtime/` and `assets/processed/masters/` are generated outputs of the project's own asset pipeline. They are provided under the same MIT License as the source code:

- `assets/processed/runtime/states/*/*.png` — unified character state PNGs
- `assets/processed/masters/actions/*.png` — generated action masters
- `assets/processed/masters/generated/*.png` — generated action masters
- `assets/processed/masters/front_base.png`, `back_base.png`, `side_base.png` — clean base views

### Source Reference Assets (Not MIT Licensed)

The following files are **not covered by the MIT License**. They are included for reference and transparency only:

- `sprites/*.png` — original character sprite source files (including `正面.png`, `侧面.png`, `背面.png`, and state expression reference files)
- `assets/references/*.png` — reference images used during asset pipeline development
- `assets/source/` — source material directory (see `assets/source/README.md`)

These reference assets may be subject to third-party rights or personal use agreements. Redistribution of these files outside this repository is not authorized.

### AI-Assisted Assets

Certain state action assets in `assets/processed/masters/generated/` were created with AI assistance (image generation and/or processing). These are treated as project-generated assets under the MIT License for the purpose of this repository.

### Preview Files

`assets/previews/` files (contact sheets, GIFs) are MIT-licensed as project documentation artifacts.

## Third-Party Marks

This is an unofficial fan-made project and is **not affiliated with or endorsed by DeepSeek (深度求索)**.

- "DeepSeek" and the DeepSeek logo are trademarks of DeepSeek (深度求索).
- "大肥鱼" (DaFeiYu / Big Fat Fish) is a character associated with DeepSeek's brand.
- All other trademarks and brand names belong to their respective owners.

## Disclaimer

Every effort has been made to accurately describe the licensing status of each asset. If you believe any file in this repository is incorrectly classified or infringes on your rights, please open an issue.