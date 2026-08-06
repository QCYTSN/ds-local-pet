#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build pre-scaled runtime art from the approved unified-character sheets.

Only derived files are written below ``assets/processed``.  The original
three-view sprites and the user's separately supplied reference poses are
never renamed, overwritten, or used as runtime frames.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class AssetSource:
    paths: tuple[str, ...]
    quality: str
    visual_scale: float = 1.0
    generated: bool = False


# ``unified_generated_v1`` is the single art family produced from the same
# green-screen character reference.  The three clean original views remain
# the canonical direction references for idle/front/back only.
ASSET_SOURCES: dict[str, AssetSource] = {
    "idle_front": AssetSource(("assets/processed/masters/front_base.png",), "clean_base_view"),
    "idle_think": AssetSource(
        ("assets/candidates/state_actions/candidate_c_daily/idle_think.png",),
        "formal_unified_generated_action",
        generated=True,
    ),
    "idle_back": AssetSource(("assets/processed/masters/back_base.png",), "clean_base_view"),
    "walk_side": AssetSource(
        tuple(
            f"assets/candidates/walk_side/candidate_a/walk_side_{index:02d}.png"
            for index in range(4)
        ),
        "formal_unified_generated_walk_frames",
        generated=True,
    ),
    "happy": AssetSource(
        ("assets/candidates/state_actions/candidate_b_core/happy.png",),
        "formal_unified_generated_action",
        generated=True,
    ),
    "talk": AssetSource(
        ("assets/candidates/state_actions/candidate_b_core/talk.png",),
        "formal_unified_generated_action",
        generated=True,
    ),
    "angry": AssetSource(
        ("assets/candidates/state_actions/candidate_c_daily/angry.png",),
        "formal_unified_generated_action",
        generated=True,
    ),
    "poke_react": AssetSource(
        ("assets/candidates/state_actions/candidate_b_core/poke_react.png",),
        "formal_unified_generated_action",
        generated=True,
    ),
    "eat": AssetSource(
        ("assets/candidates/state_actions/candidate_b_core/eat.png",),
        "formal_unified_generated_action",
        generated=True,
    ),
    "sweep": AssetSource(
        ("assets/candidates/state_actions/candidate_c_daily/sweep.png",),
        "formal_unified_generated_action",
        generated=True,
    ),
    # Reclining and seated states intentionally occupy less vertical space.
    "sleep": AssetSource(
        ("assets/candidates/state_actions/candidate_c_daily/sleep.png",),
        "formal_unified_generated_action",
        visual_scale=0.73,
        generated=True,
    ),
    "dizzy": AssetSource(
        ("assets/candidates/state_actions/candidate_d_interactions/dizzy.png",),
        "formal_unified_generated_action",
        visual_scale=0.78,
        generated=True,
    ),
    "dragging": AssetSource(
        ("assets/candidates/state_actions/candidate_d_interactions/dragging.png",),
        "formal_unified_generated_action",
        visual_scale=0.94,
        generated=True,
    ),
    "falling": AssetSource(
        ("assets/candidates/state_actions/candidate_d_interactions/falling.png",),
        "formal_unified_generated_action",
        visual_scale=0.94,
        generated=True,
    ),
}


def _primary_component(image: Image.Image) -> Image.Image:
    """Keep the main character component and drop detached prompt symbols.

    Generated sheets are keyed green, so disconnected ``Z`` marks and similar
    request artifacts become independent alpha islands.  The character, held
    fish, broom and whale pillow are one connected main component in the
    approved sheets.  This is not content reconstruction: it only discards
    detached overlay components after the green background has already been
    made transparent.
    """

    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    width, height = rgba.size
    pixels = alpha.load()
    seen = bytearray(width * height)
    largest: list[int] = []
    for y in range(height):
        for x in range(width):
            start = y * width + x
            if seen[start] or pixels[x, y] < 32:
                continue
            seen[start] = 1
            component: list[int] = []
            queue: deque[tuple[int, int]] = deque([(x, y)])
            while queue:
                current_x, current_y = queue.popleft()
                component.append(current_y * width + current_x)
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    index = next_y * width + next_x
                    if not seen[index] and pixels[next_x, next_y] >= 32:
                        seen[index] = 1
                        queue.append((next_x, next_y))
            if len(component) > len(largest):
                largest = component
    if not largest:
        raise ValueError("统一角色候选没有有效透明像素。")
    kept = bytearray(width * height)
    for index in largest:
        kept[index] = 1
    raw = list(rgba.getdata())
    rgba.putdata(
        [pixel if kept[index] else (0, 0, 0, 0) for index, pixel in enumerate(raw)]
    )
    return rgba


def _trimmed(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("无法缩放空的透明图。")
    return image.crop(bbox)


def _runtime_frames(images: list[Image.Image], visual_height: int) -> list[Image.Image]:
    """Scale a clip with a shared canvas and an invariant lower baseline."""

    trimmed = [_trimmed(image) for image in images]
    largest_height = max(image.height for image in trimmed)
    factor = visual_height / max(1, largest_height)
    scaled = [
        image.resize(
            (max(1, round(image.width * factor)), max(1, round(image.height * factor))),
            Image.Resampling.LANCZOS,
        )
        for image in trimmed
    ]
    padding = max(4, round(visual_height * 0.045))
    canvas_width = max(image.width for image in scaled) + padding * 2
    canvas_height = visual_height + padding * 2
    baseline = canvas_height - padding
    frames: list[Image.Image] = []
    for image in scaled:
        frame = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        x = (canvas_width - image.width) // 2
        y = baseline - image.height
        frame.alpha_composite(image, (x, y))
        frames.append(frame)
    return frames


def _master_path(asset_id: str, index: int, frame_count: int) -> Path:
    suffix = f"_{index:02d}" if frame_count > 1 else ""
    return PROJECT_ROOT / "assets" / "processed" / "masters" / "generated" / f"{asset_id}{suffix}.png"


def _load_source(path: Path, generated: bool) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(f"缺少素材：{path}")
    with Image.open(path) as raw:
        image = raw.convert("RGBA")
    return _primary_component(image) if generated else image


def main() -> None:
    parser = argparse.ArgumentParser(description="生成统一角色图集的运行时透明 PNG。")
    parser.add_argument(
        "--runtime-dir",
        type=Path,
        default=PROJECT_ROOT / "assets" / "processed" / "runtime" / "states",
    )
    parser.add_argument("--sizes", type=int, nargs="+", default=[187, 238, 306])
    parser.add_argument(
        "--report-out",
        type=Path,
        default=PROJECT_ROOT / "assets" / "manifests" / "runtime_inventory.json",
    )
    args = parser.parse_args()
    if any(size <= 0 for size in args.sizes):
        parser.error("--sizes 必须为正整数。")

    args.runtime_dir.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, object]] = {}
    for asset_id, source in ASSET_SOURCES.items():
        source_paths = tuple(PROJECT_ROOT / path for path in source.paths)
        masters = [_load_source(path, source.generated) for path in source_paths]
        master_paths: list[str] = []
        if source.generated:
            for index, master in enumerate(masters):
                output = _master_path(asset_id, index, len(masters))
                output.parent.mkdir(parents=True, exist_ok=True)
                master.save(output)
                master_paths.append(output.relative_to(PROJECT_ROOT).as_posix())
        else:
            master_paths = [path.relative_to(PROJECT_ROOT).as_posix() for path in source_paths]

        state_dir = args.runtime_dir / asset_id
        state_dir.mkdir(parents=True, exist_ok=True)
        frames_by_size: dict[str, list[str]] = {}
        for size in args.sizes:
            frames = _runtime_frames(masters, round(size * source.visual_scale))
            paths: list[str] = []
            for index, frame in enumerate(frames):
                suffix = f"_{index:02d}" if len(frames) > 1 else ""
                output = state_dir / f"{asset_id}_{size}{suffix}.png"
                frame.save(output)
                paths.append(output.relative_to(PROJECT_ROOT).as_posix())
            frames_by_size[str(size)] = paths
        records[asset_id] = {
            "source_masters": master_paths,
            "frames": frames_by_size,
            "frame_count": len(masters),
            "quality": source.quality,
            "art_family": "unified_generated_v1" if source.generated else "clean_three_view",
            "generated_at_runtime": False,
        }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(
        json.dumps({"assets": records}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"生成 {len(records)} 个运行时状态；尺寸：{', '.join(map(str, args.sizes))}")


if __name__ == "__main__":
    main()
