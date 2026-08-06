#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extract user-authorized state poses from white-background source images.

The paid source files under ``sprites/`` are never altered.  This tool makes
transparent, cropped masters for runtime use by retaining the main character
composition and nearby connected props, while excluding the surrounding white
canvas and isolated corner labels.
"""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
from shutil import copy2

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "sprites"
REFERENCE_DIR = PROJECT_ROOT / "assets" / "references" / "state_sources"
MASTER_DIR = PROJECT_ROOT / "assets" / "processed" / "masters" / "actions"
REPORT_PATH = PROJECT_ROOT / "assets" / "manifests" / "state_extraction_report.json"

# Asset id, original paid source, and its intended interaction state.
STATE_SOURCES = (
    ("idle_think", "发呆.png", "THINKING"),
    ("happy", "开心.png", "HAPPY"),
    ("talk", "说话.png", "TALKING"),
    ("angry", "生气.png", "ANGRY"),
    ("poke_react", "被戳.png", "POKE_REACT"),
    ("eat", "吃东西.png", "EATING"),
    ("sweep", "扫地.png", "SWEEPING"),
    ("sleep", "睡觉.png", "SLEEPING"),
    # The paid “抓取” pose reads as surprised airtime, which works for both
    # being held and the brief fall release transition.
    ("dragging", "抓取.png", "DRAGGING"),
    ("falling", "抓取.png", "FALLING"),
    ("dizzy", "眩晕.png", "DIZZY"),
)


def is_background(pixel: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = pixel
    return alpha > 0 and min(red, green, blue) >= 242 and max(red, green, blue) - min(red, green, blue) <= 16


def remove_border_background(image: Image.Image) -> Image.Image:
    """Flood-fill only the white canvas connected to image edges.

    Internal white apron, lace and eye-highlight pixels remain opaque because
    the dark outlines around the character disconnect them from the border.
    """

    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    visited = bytearray(width * height)
    queue: deque[int] = deque()

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if not visited[index] and is_background(pixels[x, y]):
            visited[index] = 1
            queue.append(index)

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                neighbor = ny * width + nx
                if not visited[neighbor] and is_background(pixels[nx, ny]):
                    visited[neighbor] = 1
                    queue.append(neighbor)
    for index, was_background in enumerate(visited):
        if was_background:
            pixels[index % width, index // width] = (0, 0, 0, 0)
    return rgba


def components(image: Image.Image) -> list[tuple[list[int], tuple[int, int, int, int]]]:
    """Return alpha-connected components with their inclusive-exclusive boxes."""

    width, height = image.size
    alpha = image.getchannel("A")
    alpha_data = alpha.load()
    visited = bytearray(width * height)
    found: list[tuple[list[int], tuple[int, int, int, int]]] = []
    for seed in range(width * height):
        if visited[seed] or alpha_data[seed % width, seed // width] <= 16:
            continue
        queue: deque[int] = deque((seed,))
        visited[seed] = 1
        pixels: list[int] = []
        left = right = seed % width
        top = bottom = seed // width
        while queue:
            index = queue.popleft()
            x, y = index % width, index // width
            pixels.append(index)
            left, right = min(left, x), max(right, x)
            top, bottom = min(top, y), max(bottom, y)
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < width and 0 <= ny < height:
                    neighbor = ny * width + nx
                    if not visited[neighbor] and alpha_data[nx, ny] > 16:
                        visited[neighbor] = 1
                        queue.append(neighbor)
        found.append((pixels, (left, top, right + 1, bottom + 1)))
    return found


def intersects(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    return first[0] < second[2] and first[2] > second[0] and first[1] < second[3] and first[3] > second[1]


def isolate_composition(image: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    transparent = remove_border_background(image)
    found = components(transparent)
    if not found:
        raise ValueError("未发现可提取角色主体")
    main_pixels, main_bbox = max(found, key=lambda item: len(item[0]))
    width, height = transparent.size
    main_width = main_bbox[2] - main_bbox[0]
    main_height = main_bbox[3] - main_bbox[1]
    expanded = (
        max(0, main_bbox[0] - max(24, round(main_width * 0.30))),
        max(0, main_bbox[1] - max(24, round(main_height * 0.24))),
        min(width, main_bbox[2] + max(24, round(main_width * 0.30))),
        min(height, main_bbox[3] + max(24, round(main_height * 0.20))),
    )
    kept = [(pixels, bbox) for pixels, bbox in found if len(pixels) >= 5 and intersects(bbox, expanded)]
    result = Image.new("RGBA", transparent.size, (0, 0, 0, 0))
    source_pixels = transparent.load()
    output_pixels = result.load()
    for component_pixels, _bbox in kept:
        for index in component_pixels:
            x, y = index % width, index // width
            output_pixels[x, y] = source_pixels[x, y]
    bbox = result.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("角色主体提取后为空")
    padding = max(5, round(max(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 0.025))
    cropped_box = (
        max(0, bbox[0] - padding),
        max(0, bbox[1] - padding),
        min(width, bbox[2] + padding),
        min(height, bbox[3] + padding),
    )
    return result.crop(cropped_box), {
        "main_component_bbox": list(main_bbox),
        "selected_component_count": len(kept),
        "detected_component_count": len(found),
        "cropped_bbox": list(cropped_box),
    }


def main() -> None:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for asset_id, source_name, action in STATE_SOURCES:
        source = SOURCE_DIR / source_name
        if not source.is_file():
            raise FileNotFoundError(f"缺少已授权动作图：{source}")
        reference = REFERENCE_DIR / source_name
        if not reference.exists():
            copy2(source, reference)
        with Image.open(source) as raw:
            extracted, extraction = isolate_composition(raw)
            source_size = raw.size
        master = MASTER_DIR / f"{asset_id}.png"
        extracted.save(master)
        records.append(
            {
                "asset_id": asset_id,
                "action": action,
                "source_file": source.relative_to(PROJECT_ROOT).as_posix(),
                "reference_file": reference.relative_to(PROJECT_ROOT).as_posix(),
                "master_file": master.relative_to(PROJECT_ROOT).as_posix(),
                "source_size": list(source_size),
                "master_size": list(extracted.size),
                "authorization": "user_authorized_paid_asset",
                "extraction": extraction,
            }
        )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps({"assets": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"提取 {len(records)} 个已授权动作 master")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
