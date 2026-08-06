#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Inspect DaFeiYu image sources without changing them.

The project deliberately keeps source pictures in ``sprites/`` untouched.  This
tool writes a factual inventory into ``assets/manifests/`` and a human-readable
report in ``docs/``.  The small set of manual notes below exists because pose
and expression are visual judgements, not safe filename guesses.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "sprites"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


# Reviewed visually on 2026-08-06.  The user authorized these paid pose images,
# but the final runtime deliberately uses one unified generated art family so
# state transitions do not swap the character's face, costume details or scale.
VISUAL_OVERRIDES: dict[str, dict[str, Any]] = {
    "正面.png": {
        "logical_name": "front_base",
        "visual_description": "正面站立，双脚接地，蓝白女仆装与围裙鲸鱼图案完整可见。",
        "pose_category": "standing",
        "direction": "front",
        "expression": "neutral",
        "anchor_type": "ground_anchor",
        "recommended_state": "idle_front",
        "recommended_motion": "breath",
        "contains_corner_mark": False,
        "quality_notes": "干净透明底三视图主参考。",
        "usable": True,
        "confidence": "high",
    },
    "侧面.png": {
        "logical_name": "side_base",
        "visual_description": "完整左侧站立视图，双脚接地，适合镜像为左右行走的基准姿势。",
        "pose_category": "standing",
        "direction": "left",
        "expression": "neutral",
        "anchor_type": "ground_anchor",
        "recommended_state": "walk_direction_reference",
        "recommended_motion": "direction_reference",
        "contains_corner_mark": False,
        "quality_notes": "干净透明底三视图主参考；不是实际走路帧，正式四帧走路另行接入。",
        "usable": True,
        "confidence": "high",
    },
    "背面.png": {
        "logical_name": "back_base",
        "visual_description": "背面站立视图，长发、发饰、鱼尾和双脚接地关系完整。",
        "pose_category": "standing",
        "direction": "back",
        "expression": "not_visible",
        "anchor_type": "ground_anchor",
        "recommended_state": "idle_back",
        "recommended_motion": "breath",
        "contains_corner_mark": False,
        "quality_notes": "干净透明底三视图主参考。",
        "usable": True,
        "confidence": "high",
    },
    "发呆.png": {
        "logical_name": "think_source_candidate",
        "visual_description": "正面站立、眼神放空的近景姿势。",
        "pose_category": "standing",
        "direction": "front",
        "expression": "thinking",
        "anchor_type": "ground_anchor",
        "recommended_state": "idle_think",
        "recommended_motion": "slow_sway",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的思考姿势参考；为保持统一角色身份，仅学习动作语义，不直接作为运行时图。",
        "usable": False,
        "confidence": "high",
    },
    "吃东西.png": {
        "logical_name": "eat_source_candidate",
        "visual_description": "正面双手举鱼靠近嘴部，适合进食动作参考。",
        "pose_category": "standing_with_prop",
        "direction": "front",
        "expression": "focused_happy",
        "anchor_type": "ground_anchor",
        "recommended_state": "eat",
        "recommended_motion": "nibble",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的进食姿势参考；仅学习动作语义，不直接作为运行时图。",
        "usable": False,
        "confidence": "high",
    },
    "开心.png": {
        "logical_name": "happy_source_candidate",
        "visual_description": "正面闭眼微笑、握拳庆祝的站立姿势。",
        "pose_category": "standing",
        "direction": "front",
        "expression": "happy",
        "anchor_type": "ground_anchor",
        "recommended_state": "happy",
        "recommended_motion": "bounce",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的开心姿势参考；仅学习动作语义，不直接作为运行时图。",
        "usable": False,
        "confidence": "high",
    },
    "扫地.png": {
        "logical_name": "sweep_source_candidate",
        "visual_description": "正面手持扫帚，扫帚向左下延伸。",
        "pose_category": "standing_with_prop",
        "direction": "front",
        "expression": "focused",
        "anchor_type": "ground_anchor",
        "recommended_state": "sweep",
        "recommended_motion": "sweep_sway",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的扫地姿势参考；扫帚扩大画面边界，运行时改用统一角色图集。",
        "usable": False,
        "confidence": "high",
    },
    "抓取.png": {
        "logical_name": "surprised_jump_source_candidate",
        "visual_description": "正面单脚离地、张嘴受惊的起跳姿势；并非被抓起或悬空拖拽姿势。",
        "pose_category": "jumping",
        "direction": "front",
        "expression": "surprised",
        "anchor_type": "body_anchor",
        "recommended_state": "poke_react",
        "recommended_motion": "recoil_bounce",
        "contains_corner_mark": True,
        "quality_notes": "文件名“抓取”与实际画面不一致，更接近受惊起跳；仅作为互动动作语义参考。",
        "usable": False,
        "confidence": "high",
    },
    "生气.png": {
        "logical_name": "angry_source_candidate",
        "visual_description": "正面叉腰、皱眉、噘嘴的站立姿势。",
        "pose_category": "standing",
        "direction": "front",
        "expression": "angry",
        "anchor_type": "ground_anchor",
        "recommended_state": "angry",
        "recommended_motion": "short_shake",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的生气姿势参考；仅学习动作语义，不直接作为运行时图。",
        "usable": False,
        "confidence": "high",
    },
    "眩晕.png": {
        "logical_name": "dizzy_source_candidate",
        "visual_description": "坐地、眼睛旋涡并有星星特效，适合眩晕恢复姿势。",
        "pose_category": "seated",
        "direction": "front",
        "expression": "dizzy",
        "anchor_type": "seat_anchor",
        "recommended_state": "dizzy",
        "recommended_motion": "decay_wobble",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的眩晕姿势参考；坐姿不能按站立高度归一化，运行时改用统一角色图集。",
        "usable": False,
        "confidence": "high",
    },
    "睡觉.png": {
        "logical_name": "sleep_source_candidate",
        "visual_description": "抱鲸鱼玩偶侧卧睡眠姿势。",
        "pose_category": "sleeping",
        "direction": "left",
        "expression": "sleeping",
        "anchor_type": "sleep_anchor",
        "recommended_state": "sleep",
        "recommended_motion": "slow_breath",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的睡姿参考；睡姿与站姿锚点不同，运行时改用统一角色图集。",
        "usable": False,
        "confidence": "high",
    },
    "被戳.png": {
        "logical_name": "poke_source_candidate",
        "visual_description": "正面双拳收在胸前、委屈防御姿势。",
        "pose_category": "standing",
        "direction": "front",
        "expression": "hurt_or_annoyed",
        "anchor_type": "ground_anchor",
        "recommended_state": "poke_react",
        "recommended_motion": "recoil",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的被戳姿势参考；仅学习动作语义，不直接作为运行时图。",
        "usable": False,
        "confidence": "high",
    },
    "说话.png": {
        "logical_name": "talk_source_candidate",
        "visual_description": "正面张嘴举手的问候/说话姿势。",
        "pose_category": "standing",
        "direction": "front",
        "expression": "talking",
        "anchor_type": "ground_anchor",
        "recommended_state": "talk",
        "recommended_motion": "talk_nod",
        "contains_corner_mark": True,
        "quality_notes": "用户授权的说话姿势参考；仅学习动作语义，不直接作为运行时图。",
        "usable": False,
        "confidence": "high",
    },
}


def estimate_bbox(image: Image.Image) -> list[int] | None:
    """Return an approximate visible bbox without modifying the image."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    alpha_bbox = alpha.getbbox()
    if alpha_bbox and alpha.getextrema()[0] < 250:
        return list(alpha_bbox)

    # Opaque pictures are usually white-background source candidates.  Treat
    # strongly non-white pixels as a rough foreground estimate.  Corner marks
    # can influence this result, which is recorded in quality_notes.
    rgb = rgba.convert("RGB")
    mask = Image.new("L", rgb.size)
    source = rgb.load()
    target = mask.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            red, green, blue = source[x, y]
            target[x, y] = 255 if min(red, green, blue) < 225 else 0
    bbox = mask.getbbox()
    return list(bbox) if bbox else None


def default_record(path: Path, source_dir: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
        bbox = estimate_bbox(image)
        alpha_min, alpha_max = image.convert("RGBA").getchannel("A").getextrema()
    return {
        "source_file": path.relative_to(PROJECT_ROOT).as_posix(),
        "logical_name": f"unclassified_{path.stem}",
        "visual_description": "尚未分类的图像资源。",
        "pose_category": "unknown",
        "direction": "unknown",
        "expression": "unknown",
        "original_width": width,
        "original_height": height,
        "character_bbox": bbox,
        "character_visual_height": (bbox[3] - bbox[1]) if bbox else 0,
        "anchor_type": "unknown",
        "recommended_state": None,
        "recommended_motion": None,
        "contains_corner_mark": False,
        "quality_notes": "自动发现；尚未作为正式状态资产使用。",
        "usable": False,
        "runtime_usage": "not_selected",
        "user_authorized": False,
        "confidence": "low",
        "has_alpha": alpha_min < 255 or alpha_max < 255,
        "source_directory": source_dir.relative_to(PROJECT_ROOT).as_posix(),
    }


def inventory(source_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(source_dir.iterdir(), key=lambda value: value.name):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        record = default_record(path, source_dir)
        override = VISUAL_OVERRIDES.get(path.name)
        if override:
            record.update(override)
            if record.get("contains_corner_mark"):
                record["user_authorized"] = True
                record["runtime_usage"] = "motion_reference_only"
            else:
                record["runtime_usage"] = "clean_base_reference"
        elif path.name == "icon.png":
            record.update(
                {
                    "logical_name": "app_icon",
                    "visual_description": "应用托盘图标。",
                    "pose_category": "icon",
                    "direction": "na",
                    "expression": "na",
                    "anchor_type": "na",
                    "quality_notes": "非角色状态资产。",
                    "confidence": "high",
                }
            )
        elif "_" in path.stem and path.stem.rsplit("_", 1)[-1].isdigit():
            record.update(
                {
                    "logical_name": f"legacy_runtime_{path.stem}",
                    "visual_description": "旧版预缩放三视图衍生文件。",
                    "pose_category": "legacy_runtime",
                    "direction": "derived",
                    "expression": "neutral",
                    "anchor_type": "ground_anchor",
                    "quality_notes": "保留兼容性，不作为新资产管线的源文件。",
                    "usable": True,
                    "runtime_usage": "legacy_compatibility_only",
                    "confidence": "high",
                }
            )
        records.append(record)
    return records


def write_markdown(records: list[dict[str, Any]], output: Path) -> None:
    lines = [
        "# 角色素材盘点",
        "",
        "本报告来自逐图视觉核验与元数据扫描。原始图片均保留在 `sprites/`，没有被改名、移动或覆盖。",
        "",
        "## 结论",
        "",
        "- 三视图（正面、侧面、背面）是干净透明底，可作为正式资产管线的基础参考。",
        "- 十张付费状态图已获用户授权；为避免状态切换时角色细节跳变，它们只用于学习动作语义，最终运行时改用统一角色图集。",
        "- `抓取.png` 实际是受惊起跳，不适合作为被抓起或拖拽状态。",
        "- 侧面图是静态站姿，不是走路帧；正式运行时已接入统一角色的四帧侧视走路循环。",
        "",
        "## 逐图记录",
        "",
        "| 文件 | 逻辑名 | 姿势 / 表情 | 建议状态 | 可直接使用 | 备注 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in records:
        lines.append(
            "| `{source_file}` | `{logical_name}` | {pose_category} / {expression} | {recommended_state} | {usable} | {quality_notes} |".format(
                **item
            )
        )
    lines.extend(
        [
            "",
            "完整机器可读记录见 `assets/manifests/source_inventory.json`。",
            "",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="盘点桌宠角色图片，绝不改写源图片。")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=PROJECT_ROOT / "assets" / "manifests" / "source_inventory.json",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=PROJECT_ROOT / "docs" / "ASSET_INVENTORY.md",
    )
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    if not source_dir.is_dir():
        parser.error(f"找不到素材目录：{source_dir}")
    records = inventory(source_dir)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps({"source_directory": str(source_dir), "assets": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(records, args.report_out)
    print(f"盘点 {len(records)} 个图像文件")
    print(args.json_out)
    print(args.report_out)


if __name__ == "__main__":
    main()
