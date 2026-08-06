# -*- coding: utf-8 -*-
"""Create clean pre-scaled sprites from transparent DaFeiYu source views."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent
VIEW_NAMES = ("正面", "侧面", "背面")
SIZES = (187, 238, 306)


def decontaminate(image: Image.Image) -> Image.Image:
    """Recover edge colours blended against white before the image was exported."""
    image = image.convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if not 0 < alpha < 255:
                continue
            if alpha < 40:
                pixels[x, y] = (0, 0, 0, 0)
                continue
            opacity = alpha / 255.0
            pixels[x, y] = (
                int(max(0, min(255, (red - 255 * (1 - opacity)) / opacity))),
                int(max(0, min(255, (green - 255 * (1 - opacity)) / opacity))),
                int(max(0, min(255, (blue - 255 * (1 - opacity)) / opacity))),
                alpha,
            )
    return image


def premultiplied_resize(image: Image.Image, height: int) -> Image.Image:
    """Resize using black/white composites to avoid pale translucent halos."""
    width = max(1, round(image.width * height / image.height))
    black = Image.new("RGBA", image.size, (0, 0, 0, 255))
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    against_black = Image.alpha_composite(black, image).resize(
        (width, height), Image.Resampling.LANCZOS
    )
    against_white = Image.alpha_composite(white, image).resize(
        (width, height), Image.Resampling.LANCZOS
    )
    black_pixels, white_pixels = against_black.load(), against_white.load()
    output = Image.new("RGBA", (width, height))
    pixels = output.load()
    for y in range(height):
        for x in range(width):
            black_rgb = black_pixels[x, y]
            white_rgb = white_pixels[x, y]
            alpha = 255 - max(
                white_rgb[0] - black_rgb[0],
                white_rgb[1] - black_rgb[1],
                white_rgb[2] - black_rgb[2],
            )
            if alpha < 6:
                pixels[x, y] = (0, 0, 0, 0)
                continue
            opacity = alpha / 255.0
            pixels[x, y] = (
                int(max(0, min(255, black_rgb[0] / opacity))),
                int(max(0, min(255, black_rgb[1] / opacity))),
                int(max(0, min(255, black_rgb[2] / opacity))),
                alpha,
            )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="生成预处理后的多尺寸桌宠精灵。")
    parser.add_argument("input_dir", type=Path, help="包含透明 正面.png、侧面.png、背面.png 的目录。")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "sprites",
        help="输出目录，默认是项目 sprites 目录。",
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=SIZES,
        help="要生成的精灵高度列表，默认 187 238 306。",
    )
    arguments = parser.parse_args()
    if any(size <= 0 for size in arguments.sizes):
        parser.error("--sizes 必须全部为正数。")

    input_dir = arguments.input_dir.resolve()
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in VIEW_NAMES:
        source = input_dir / f"{name}.png"
        if not source.exists():
            parser.error(f"缺少输入文件：{source}")
        with Image.open(source) as raw:
            cleaned = decontaminate(raw.convert("RGBA"))
        for height in arguments.sizes:
            output = output_dir / f"{name}_{height}.png"
            image = premultiplied_resize(cleaned, height)
            image.save(output)
            print(f"{output.name}: {image.size}")

    icon_source = output_dir / "正面_187.png"
    if icon_source.exists():
        with Image.open(icon_source) as raw:
            icon = premultiplied_resize(raw.convert("RGBA"), 64)
        icon.save(output_dir / "icon.png")
        print(f"icon -> {output_dir / 'icon.png'}")


if __name__ == "__main__":
    main()
