#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Split a generated 2x2 key-pose sheet into transparent action candidates.

The input is always kept untouched.  The tool only keys the deliberately
uniform green background and writes a new candidate folder, so a sheet can be
reviewed before its extracted frames are published as runtime art.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KEY = (0, 255, 0)
DEFAULT_POSE_NAMES = ("happy", "poke_react", "talk", "eat")


def remove_green(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, _alpha = pixels[x, y]
            distance = max(abs(red - KEY[0]), abs(green - KEY[1]), abs(blue - KEY[2]))
            if distance <= 18 or (green > red + 36 and green > blue + 36):
                pixels[x, y] = (0, 0, 0, 0)
    return rgba


def main() -> None:
    parser = argparse.ArgumentParser(description="切分四格状态动作候选并移除绿色键控背景。")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--candidate", default="candidate_b")
    parser.add_argument(
        "--poses",
        nargs=4,
        metavar="POSE",
        default=DEFAULT_POSE_NAMES,
        help="四格从左上到右下的逻辑动作名。",
    )
    parser.add_argument(
        "--approved",
        action="store_true",
        help="标记为用户已认可的统一角色候选；仍不会覆盖任何源素材。",
    )
    args = parser.parse_args()

    source = args.input.resolve()
    if not source.is_file():
        parser.error(f"找不到候选图：{source}")
    destination = PROJECT_ROOT / "assets" / "candidates" / "state_actions" / args.candidate
    pose_names = tuple(args.poses)
    if len(set(pose_names)) != len(pose_names):
        parser.error("--poses 不能包含重复动作名。")
    expected = [destination / f"{name}.png" for name in pose_names]
    if any(path.exists() for path in expected):
        parser.error("候选帧已存在；为避免覆盖，请使用新的候选名称。")
    with Image.open(source) as raw:
        sheet = raw.convert("RGBA")
    if sheet.width % 2 or sheet.height % 2:
        parser.error("候选图必须是严格的 2x2 网格。")

    cell_width, cell_height = sheet.width // 2, sheet.height // 2
    destination.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    for index, (name, output) in enumerate(zip(pose_names, expected, strict=True)):
        col, row = index % 2, index // 2
        frame = sheet.crop(
            (col * cell_width, row * cell_height, (col + 1) * cell_width, (row + 1) * cell_height)
        )
        transparent = remove_green(frame)
        transparent.save(output)
        frames.append(transparent)

    preview = PROJECT_ROOT / "assets" / "previews" / "gifs" / f"state_actions_{args.candidate}_4poses.gif"
    preview.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        preview,
        save_all=True,
        append_images=frames[1:],
        duration=900,
        loop=0,
        disposal=2,
    )
    metadata = {
        "candidate": args.candidate,
        "source_sheet": str(source.relative_to(PROJECT_ROOT)),
        "grid": "2x2",
        "poses": list(pose_names),
        "frames": [path.name for path in expected],
        "preview": str(preview.relative_to(PROJECT_ROOT)),
        "review_only": not args.approved,
        "formal_runtime": bool(args.approved),
        "approved_by_user": bool(args.approved),
        "generated_at_runtime": False,
        "notes": [
            "Generated key-pose sheet extracted from a uniform chroma-key background.",
            "The sheet was generated on #00FF00 and only that background was keyed to alpha.",
            "No original asset was replaced, renamed, cropped, or reconstructed.",
        ],
    }
    (destination / "candidate.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"已写入 {destination}")
    print(preview)


if __name__ == "__main__":
    main()
