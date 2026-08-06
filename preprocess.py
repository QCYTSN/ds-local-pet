# -*- coding: utf-8 -*-
"""Cut out three source views and normalize them into transparent sprites."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parent
VIEW_NAMES = ("正面", "侧面", "背面")


def cutout(path: Path, target_height: int) -> Image.Image:
    with Image.open(path) as source:
        image = source.convert("RGBA")
    width, height = image.size
    for start_x, start_y in (
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    ):
        ImageDraw.floodfill(image, (start_x, start_y), (0, 0, 0, 0), thresh=30)

    # Remove bright anti-aliased halos adjacent to transparency.
    for _ in range(3):
        pixels = image.load()
        changed = False
        for y in range(height):
            for x in range(width):
                red, green, blue, alpha = pixels[x, y]
                if alpha == 0 or min(red, green, blue) <= 215:
                    continue
                for offset_x, offset_y in (
                    (1, 0),
                    (-1, 0),
                    (0, 1),
                    (0, -1),
                    (1, 1),
                    (-1, -1),
                    (1, -1),
                    (-1, 1),
                ):
                    neighbor_x, neighbor_y = x + offset_x, y + offset_y
                    if (
                        0 <= neighbor_x < width
                        and 0 <= neighbor_y < height
                        and pixels[neighbor_x, neighbor_y][3] == 0
                    ):
                        pixels[x, y] = (0, 0, 0, 0)
                        changed = True
                        break
        if not changed:
            break

    bounds = image.getbbox()
    if bounds is None:
        raise RuntimeError(f"{path} 抠图后为空。")
    image = image.crop(bounds)
    scaled_width = max(1, round(image.width * target_height / image.height))
    return image.resize((scaled_width, target_height), Image.Resampling.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser(description="将正面、侧面、背面白底图抠成统一透明精灵。")
    parser.add_argument("input_dir", type=Path, help="包含 正面.png、侧面.png、背面.png 的目录。")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "sprites",
        help="输出目录，默认是项目 sprites 目录。",
    )
    parser.add_argument("--height", type=int, default=340, help="统一后的角色高度，默认 340。")
    arguments = parser.parse_args()
    if arguments.height <= 0:
        parser.error("--height 必须是正数。")

    input_dir = arguments.input_dir.resolve()
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in VIEW_NAMES:
        source = input_dir / f"{name}.png"
        if not source.exists():
            parser.error(f"缺少输入文件：{source}")
        image = cutout(source, arguments.height)
        output = output_dir / f"{name}.png"
        image.save(output)
        print(f"{name}: {image.size} -> {output}")

    icon = Image.open(output_dir / "正面.png").convert("RGBA")
    icon.thumbnail((64, 64), Image.Resampling.LANCZOS)
    icon.save(output_dir / "icon.png")
    print(f"icon -> {output_dir / 'icon.png'}")


if __name__ == "__main__":
    main()
