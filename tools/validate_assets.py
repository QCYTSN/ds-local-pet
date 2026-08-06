#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate formal runtime assets and the approved unified art family."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def inspect_alpha(path: Path, label: str, problems: list[str]) -> None:
    if not path.is_file():
        problems.append(f"{label} 缺少文件：{path.relative_to(PROJECT_ROOT)}")
        return
    with Image.open(path) as image:
        alpha = image.convert("RGBA").getchannel("A")
        if alpha.getbbox() is None:
            problems.append(f"{label} 是空透明图：{path.name}")
        if alpha.getextrema()[0] == 255:
            problems.append(f"{label} 没有透明通道：{path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="校验统一角色动作 manifest 与运行时 PNG。")
    parser.add_argument("--actions", type=Path, default=PROJECT_ROOT / "assets" / "manifests" / "actions.json")
    parser.add_argument(
        "--walk-candidate-dir",
        type=Path,
        default=PROJECT_ROOT / "assets" / "candidates" / "walk_side" / "candidate_a",
    )
    args = parser.parse_args()
    actions = load_json(args.actions)
    problems: list[str] = []
    assets = actions.get("assets", {})
    serialized = json.dumps(actions, ensure_ascii=False)
    if "assets/references/state_sources" in serialized:
        problems.append("正式 manifest 不得引用付费姿势参考图。")
    if "sprites/发呆.png" in serialized:
        problems.append("正式 manifest 不得直接引用原始付费姿势图。")

    for asset_id, asset in assets.items():
        if not isinstance(asset, dict):
            problems.append(f"{asset_id} 的资产记录不是对象。")
            continue
        masters = asset.get("source_masters", [])
        if not masters:
            problems.append(f"{asset_id} 缺少 source_masters。")
        for master in masters:
            master_path = PROJECT_ROOT / str(master)
            if not master_path.is_file():
                problems.append(f"{asset_id} 缺少 master：{master}")
        for size, frames in asset.get("frames", {}).items():
            if not isinstance(frames, list) or not frames:
                problems.append(f"{asset_id}/{size} 没有运行时帧。")
                continue
            for frame in frames:
                inspect_alpha(PROJECT_ROOT / str(frame), f"{asset_id}/{size}", problems)

    for action_id, action in actions.get("actions", {}).items():
        asset_id = action.get("asset")
        if asset_id not in assets:
            problems.append(f"{action_id} 引用了未定义资源：{asset_id}")
        anchor = action.get("anchor", {})
        if not 0 <= float(anchor.get("x", -1)) <= 1 or not 0 <= float(anchor.get("y", -1)) <= 1:
            problems.append(f"{action_id} 的 anchor 超出 0..1。")

    walking = actions.get("actions", {}).get("WALKING", {})
    walk_asset = assets.get(walking.get("asset"), {}) if isinstance(walking, dict) else {}
    if walking.get("asset") != "walk_side":
        problems.append("WALKING 必须使用 walk_side。")
    if walking.get("requires_real_frames"):
        problems.append("WALKING 不应仍标记为 requires_real_frames。")
    if str(walking.get("quality")) != "formal_unified_generated_walk_frames":
        problems.append("WALKING 没有标记为正式统一角色四帧。")
    if isinstance(walk_asset, dict) and int(walk_asset.get("frame_count", 0)) != 4:
        problems.append("walk_side 必须恰好包含四帧。")

    candidate_metadata = args.walk_candidate_dir / "candidate.json"
    if not candidate_metadata.is_file():
        problems.append("缺少正式走路候选元数据。")
    else:
        candidate = load_json(candidate_metadata)
        if candidate.get("review_only") is not False or candidate.get("formal_runtime") is not True:
            problems.append("走路候选未标记为已获授权的 formal_runtime。")
        frames = candidate.get("frames", [])
        if len(frames) != 4:
            problems.append("走路候选必须恰好包含四帧。")
        for frame_name in frames:
            inspect_alpha(args.walk_candidate_dir / str(frame_name), "走路候选", problems)
        preview = PROJECT_ROOT / "assets" / "previews" / "gifs" / "walk_side_candidate_a_8fps.gif"
        if not preview.is_file():
            problems.append("走路候选缺少 8 FPS GIF 预览。")

    if problems:
        print("素材校验失败：")
        print("\n".join(f"- {problem}" for problem in problems))
        raise SystemExit(1)
    print(
        f"素材校验通过：{len(assets)} 个资产，"
        f"{len(actions.get('actions', {}))} 个动作，走路为正式四帧循环。"
    )


if __name__ == "__main__":
    main()
