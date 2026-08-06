#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create non-destructive transparent masters from the three clean base views."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_VIEWS = {
    "正面.png": ("front_base", "front"),
    "侧面.png": ("side_base", "left"),
    "背面.png": ("back_base", "back"),
}


def _is_near_white(pixel: tuple[int, int, int, int]) -> bool:
    red, green, blue, _alpha = pixel
    return min(red, green, blue) >= 225 and max(red, green, blue) - min(red, green, blue) <= 38


def remove_connected_background(image: Image.Image) -> Image.Image:
    """Only remove corner-connected pale background; preserve internal white cloth."""
    rgba = image.convert("RGBA")
    if rgba.getchannel("A").getextrema()[0] < 250:
        return rgba

    pixels = rgba.load()
    width, height = rgba.size
    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque(
        [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    )
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited or not (0 <= x < width and 0 <= y < height):
            continue
        visited.add((x, y))
        if not _is_near_white(pixels[x, y]):
            continue
        pixels[x, y] = (0, 0, 0, 0)
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return rgba


def trimmed_with_padding(image: Image.Image, padding: int = 8) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("抠图后未检测到角色像素")
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image.width, bbox[2] + padding)
    bottom = min(image.height, bbox[3] + padding)
    return image.crop((left, top, right, bottom))


def main() -> None:
    parser = argparse.ArgumentParser(description="从三张干净三视图导出透明 master，不触碰源图。")
    parser.add_argument("--source-dir", type=Path, default=PROJECT_ROOT / "sprites")
    parser.add_argument("--references-dir", type=Path, default=PROJECT_ROOT / "assets" / "references")
    parser.add_argument("--masters-dir", type=Path, default=PROJECT_ROOT / "assets" / "processed" / "masters")
    parser.add_argument("--report-out", type=Path, default=PROJECT_ROOT / "assets" / "manifests" / "extraction_report.json")
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    args.references_dir.mkdir(parents=True, exist_ok=True)
    args.masters_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    for filename, (logical_name, direction) in BASE_VIEWS.items():
        source = source_dir / filename
        if not source.is_file():
            parser.error(f"缺少基础视图：{source}")
        with Image.open(source) as raw:
            reference = raw.convert("RGBA")
        reference_path = args.references_dir / f"{logical_name}.png"
        reference.save(reference_path)
        master = trimmed_with_padding(remove_connected_background(reference))
        master_path = args.masters_dir / f"{logical_name}.png"
        master.save(master_path)
        alpha_bbox = master.getchannel("A").getbbox()
        results.append(
            {
                "logical_name": logical_name,
                "source_file": source.relative_to(PROJECT_ROOT).as_posix(),
                "reference_file": reference_path.relative_to(PROJECT_ROOT).as_posix(),
                "master_file": master_path.relative_to(PROJECT_ROOT).as_posix(),
                "direction": direction,
                "source_size": list(reference.size),
                "master_size": list(master.size),
                "character_bbox": list(alpha_bbox) if alpha_bbox else None,
                "has_alpha": master.getchannel("A").getextrema()[0] < 255,
            }
        )
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps({"masters": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"masters": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
