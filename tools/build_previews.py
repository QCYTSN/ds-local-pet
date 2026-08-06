#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate local-only visual previews of the current asset and effect setup."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def frames_for(asset: dict[str, Any], size: int) -> list[Path]:
    choices = asset.get("frames", {})
    available = sorted((int(key) for key in choices), key=lambda key: abs(key - size))
    if not available:
        raise ValueError("资源没有运行时帧")
    return [PROJECT_ROOT / path for path in choices[str(available[0])]]


def params(effect: str, phase: float) -> tuple[float, float, float, float, float]:
    """Return dx, dy, scale_x, scale_y, rotation. Effects are intentionally small."""
    sine = math.sin(phase * math.tau)
    if effect == "breath":
        return 0, 0, 1.0 - sine * 0.003, 1.0 + sine * 0.008, 0
    if effect == "think":
        return 0, abs(sine) * 1.8, 1, 1, sine * 1.5
    if effect == "walk_placeholder":
        return 0, -abs(sine) * 4.0, 1.0 + sine * 0.008, 1.0 - sine * 0.012, sine * 0.8
    if effect == "walk_frames":
        return 0, -abs(sine) * 0.8, 1.0, 1.0, 0
    if effect == "bounce":
        return 0, -abs(sine) * 11.0, 1.0 + abs(sine) * 0.025, 1.0 - abs(sine) * 0.03, 0
    if effect == "talk":
        return 0, sine * 1.2, 1, 1, sine * 0.45
    if effect == "angry":
        return sine * 3.0, 0, 1, 1, sine * 1.7
    if effect == "recoil":
        return 0, abs(sine) * 3, 1.0 - abs(sine) * 0.04, 1.0 + abs(sine) * 0.025, 0
    if effect == "eat":
        return 0, abs(sine) * 2, 1.0 + abs(sine) * 0.018, 1.0 - abs(sine) * 0.022, 0
    if effect == "sweep":
        return sine * 2, 0, 1, 1, sine * 2.1
    if effect == "sleep":
        return 0, 0, 1.0 - sine * 0.003, 1.0 + sine * 0.006, 0
    if effect == "float":
        return 0, sine * 3, 1, 1, sine * 1.0
    if effect == "fall":
        return 0, phase * 6, 1, 1, 0
    if effect == "dizzy":
        amplitude = max(0.25, 1 - phase) * 5
        return sine * amplitude, 0, 1, 1, sine * amplitude
    return 0, 0, 1, 1, 0


def transformed(image: Image.Image, effect: str, phase: float, canvas_size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGBA")
    dx, dy, scale_x, scale_y, angle = params(effect, phase)
    scaled = image.resize(
        (max(1, round(image.width * scale_x)), max(1, round(image.height * scale_y))),
        Image.Resampling.LANCZOS,
    )
    scaled = scaled.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    x = round((canvas.width - scaled.width) / 2 + dx)
    y = round(canvas.height - scaled.height - 18 + dy)
    canvas.alpha_composite(scaled, (x, y))
    return canvas


def contact_sheet(images: list[tuple[str, Image.Image]], output: Path) -> None:
    cell_w, cell_h = 300, 350
    columns = 4
    rows = math.ceil(len(images) / columns)
    sheet = Image.new("RGBA", (cell_w * columns, cell_h * rows), (15, 25, 56, 255))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        col, row = index % columns, index // columns
        frame = transformed(image, "breath", 0.25, (cell_w, cell_h - 25))
        sheet.alpha_composite(frame, (col * cell_w, row * cell_h + 25))
        draw.text((col * cell_w + 12, row * cell_h + 7), label, fill=(219, 235, 255, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成运行时状态与程序化动作的 GIF 预览。")
    parser.add_argument("--actions", type=Path, default=PROJECT_ROOT / "assets" / "manifests" / "actions.json")
    parser.add_argument("--size", type=int, default=238)
    parser.add_argument("--frames", type=int, default=12)
    args = parser.parse_args()
    manifest = load_json(args.actions)
    gifs = PROJECT_ROOT / "assets" / "previews" / "gifs"
    contact = PROJECT_ROOT / "assets" / "previews" / "contact_sheet" / "runtime_states.png"
    gifs.mkdir(parents=True, exist_ok=True)
    contact_items: list[tuple[str, Image.Image]] = []
    for action_id, action in manifest["actions"].items():
        asset = manifest["assets"][action["asset"]]
        paths = frames_for(asset, args.size)
        images: list[Image.Image] = []
        for path in paths:
            with Image.open(path) as raw:
                images.append(raw.convert("RGBA"))
        image = images[0]
        canvas_size = (
            max(360, max(frame.width for frame in images) + 72),
            max(380, max(frame.height for frame in images) + 62),
        )
        effect = action["procedural_motion"]["type"]
        frames = [
            transformed(images[index % len(images)], effect, index / args.frames, canvas_size)
            for index in range(args.frames)
        ]
        frames[0].save(
            gifs / f"{action_id.lower()}.gif",
            save_all=True,
            append_images=frames[1:],
            duration=125,
            loop=0,
            disposal=2,
        )
        contact_items.append((action_id, image))
    contact_sheet(contact_items, contact)
    print(f"生成 {len(contact_items)} 个 GIF 预览")
    print(contact)


if __name__ == "__main__":
    main()
