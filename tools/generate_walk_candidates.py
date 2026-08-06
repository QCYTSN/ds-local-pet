#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Package externally generated walk candidates into review-only GIF previews.

Image generation itself stays in the authorised Codex image tool.  This script
never fabricates frames and never promotes a candidate into the formal manifest.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="把四张候选走路帧打包成仅供评审的 GIF。")
    parser.add_argument("candidate", choices=["candidate_a", "candidate_b"])
    parser.add_argument("--source-dir", type=Path, default=PROJECT_ROOT / "assets" / "candidates" / "walk_side")
    parser.add_argument("--fps", type=int, choices=[8, 12], default=8)
    args = parser.parse_args()
    directory = args.source_dir / args.candidate
    frames = sorted(directory.glob("walk_side_*.png"))
    if len(frames) != 4:
        parser.error(f"{directory} 必须包含四张 walk_side_*.png，当前为 {len(frames)} 张")
    loaded: list[Image.Image] = []
    for frame in frames:
        with Image.open(frame) as raw:
            loaded.append(raw.convert("RGBA"))
    widths = {image.width for image in loaded}
    heights = {image.height for image in loaded}
    if len(widths) != 1 or len(heights) != 1:
        parser.error("四张候选帧必须具有相同画布尺寸")
    output = PROJECT_ROOT / "assets" / "previews" / "gifs" / f"walk_side_{args.candidate}_{args.fps}fps.gif"
    output.parent.mkdir(parents=True, exist_ok=True)
    loaded[0].save(
        output,
        save_all=True,
        append_images=loaded[1:],
        duration=round(1000 / args.fps),
        loop=0,
        disposal=2,
    )
    print(output)


if __name__ == "__main__":
    main()
