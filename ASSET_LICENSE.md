# Asset License & Copyright

This document describes licensing for **source code** and for **visual assets**
separately. They are not governed by the same terms.

## Source Code — MIT License

The source code in this repository is licensed under the **MIT License**
(see [LICENSE](LICENSE)), unless otherwise stated in individual files.

The MIT License applies to:

- All `.py` files in `app/`, `animation/`, `pet/`, `awareness/`, `behavior/`, `dialogue/`, `settings/`, `tools/`, `tests/`
- `main.py`, `桌宠.py`, `preprocess.py`, `preprocess2.py`, `make_zip.py`
- Build scripts, CI configuration, and documentation
- Text resources authored for this project (`assets/dialogue/*.json`, `assets/app_categories.json`, `assets/privacy_rules.json`)
- Runtime manifests authored by this project's tooling (`assets/manifests/*.json`)

### Upstream Code

This project is based on the MIT-licensed
[1190fasheqi/dafeiyu-pet](https://github.com/1190fasheqi/dafeiyu-pet).
The original MIT license is preserved in [LICENSE](LICENSE), and full
attribution is in [CREDITS.md](CREDITS.md).

## Visual Character Assets — Not Covered by MIT

**Visual character assets are not covered by the MIT source-code license unless
explicitly stated otherwise.**

They are distributed for use with this project, subject to any applicable
third-party rights, platform terms, and original asset agreements. No
additional license is granted here, and no warranty is made about the
provenance or clearance of the underlying character artwork.

This applies to the image content of, among others:

- `assets/processed/runtime/` — runtime character state PNGs
- `assets/processed/masters/` — processed masters used to derive runtime frames
- `assets/candidates/` — approved key-pose and walk-cycle sheets
- `assets/previews/` — contact sheets and GIF previews rendered from the above
- `sprites/*.png` — character view images inherited from the upstream project

### Origin of the Bundled Artwork

Stated as fact, without any conclusion about ownership:

- The three base character views (`sprites/正面.png`, `sprites/侧面.png`,
  `sprites/背面.png` and their resized variants) were imported from the upstream
  project at baseline commit `2822f8f`, which describes them as fan-made
  ("二创") character art.
- `assets/processed/masters/` and `assets/processed/runtime/` are outputs of
  this project's own pipeline (background keying, trimming, alpha cleanup and
  size normalisation) applied to the images described above and to the
  generated sheets described below.
- Processing, re-encoding or resizing an image does not by itself change the
  rights in the underlying artwork.

### AI-Assisted Assets

Some key-pose and walk-cycle assets — the sheets under `assets/candidates/`,
the files under `assets/processed/masters/generated/`, and the runtime frames
derived from them — were produced with AI assistance (image generation and/or
image processing), then chroma-keyed and normalised by this project's tooling.

This is a statement of origin only. It does not imply that these files are
MIT-licensed, public domain, or free of third-party claims.

### Source Reference Assets — Not Distributed Here

The following are **not distributed in this public repository** and are **not
included in release builds**:

- `assets/source/` — source material working directory
- `assets/references/` — reference images used during pipeline development
- The paid state-pose reference files under `sprites/`
  (`发呆.png`, `吃东西.png`, `开心.png`, `扫地.png`, `抓取.png`, `生气.png`,
  `眩晕.png`, `睡觉.png`, `被戳.png`, `说话.png`)

These files are excluded via [`.gitignore`](.gitignore) and by the release
packaging whitelist in `tools/build_release.py`. They are held locally by the
project author under separate terms and are not redistributed.

## Third-Party Marks

This is an unofficial fan-made project and is **not affiliated with or endorsed
by DeepSeek (深度求索)**.

- "DeepSeek" and the DeepSeek logo are trademarks of DeepSeek (深度求索).
- This project uses community/fan-created DeepSeek-related character imagery.
- DeepSeek-related names, marks and branding belong to their respective owners.
- All other trademarks and brand names belong to their respective owners.

## Disclaimer

Every effort has been made to describe the origin of each asset accurately.
If you believe any file in this repository is incorrectly described or
infringes on your rights, please open an issue and it will be removed or
corrected.
