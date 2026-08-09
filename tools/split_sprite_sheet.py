#!/usr/bin/env python
"""Split a transparent, evenly gridded sprite sheet into trimmed PNG frames."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def _trim(frame: Image.Image) -> Image.Image:
    alpha = frame.getchannel("A")
    # Ignore tiny antialiasing residue left by chroma-key removal.
    mask = alpha.point(lambda value: 255 if value >= 12 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("sprite sheet cell contains no visible pixels")
    return frame.crop(bbox)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--columns", type=int, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    if args.rows <= 0 or args.columns <= 0:
        parser.error("--rows and --columns must be positive")

    with Image.open(args.input) as source:
        sheet = source.convert("RGBA")
    cell_width = sheet.width // args.columns
    cell_height = sheet.height // args.rows
    if cell_width <= 0 or cell_height <= 0:
        raise ValueError("sprite sheet is smaller than its requested grid")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for row in range(args.rows):
        for column in range(args.columns):
            left = column * cell_width
            top = row * cell_height
            right = sheet.width if column == args.columns - 1 else left + cell_width
            bottom = sheet.height if row == args.rows - 1 else top + cell_height
            frame = _trim(sheet.crop((left, top, right, bottom)))
            output = args.out_dir / f"{args.prefix}_{count:02d}.png"
            frame.save(output)
            count += 1
    print(f"wrote {count} frames to {args.out_dir}")


if __name__ == "__main__":
    main()
