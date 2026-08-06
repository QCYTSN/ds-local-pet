#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Write the unified-character asset contract and animation manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return fallback


def character_spec() -> dict[str, Any]:
    return {
        "character_id": "dafeiyu",
        "display_name": "大肥鱼",
        "reference_views": {
            "front": "assets/references/front_base.png",
            "side": "assets/references/side_base.png",
            "back": "assets/references/back_base.png",
            "unified_action_family": "assets/candidates/state_actions/candidate_b_core/source_sheet.png",
        },
        "visual_language": {
            "proportion": "Q版大头小身，头部约占可见角色高度的 45%–50%，四肢短小。",
            "head_to_body_ratio": "头部显著大于躯干；禁止生成成熟人体比例。",
            "face": "大而低位的蓝色渐变眼睛，圆润浅色脸颊，细黑描边。",
            "hair": "深海军蓝到浅蓝渐变的长发，顶部有一撮向上弯曲的呆毛。",
            "headwear": "白色荷叶边女仆头饰，蓝色侧边蝴蝶结。",
            "side_ornaments": "两侧有鱼鳍/翼状发饰；镜像时保持装饰与朝向一致。",
            "outfit": "蓝白女仆装、深蓝蝴蝶结、白色围裙；围裙中央固定鲸鱼图案。",
            "skirt": "深蓝裙摆带金色海洋主题装饰与白色荷叶边。",
            "footwear": "短袜和深蓝色圆头鞋。",
            "tail": "右后方延伸的蓝色鱼尾，保持鱼尾形态，不能替换成普通动物尾巴。",
            "linework": "干净的深色描边，Q版插画线条，轮廓清晰。",
        },
        "palette": {
            "hair_deep": "#33457F",
            "hair_light": "#69BEEB",
            "dress_navy": "#182557",
            "apron_white": "#F6F3F5",
            "bow_blue": "#62C5EF",
            "accent_gold": "#D8B77A",
            "eye_blue": "#4FBBEA",
        },
        "non_negotiable_invariants": [
            "保持 Q 版大头小身比例、同一张脸和同一眼睛位置。",
            "保持蓝白女仆装、围裙中央鲸鱼图案和白色头饰。",
            "保持顶部呆毛、蓝色侧边蝴蝶结、发型轮廓和发色渐变。",
            "保持蓝色鱼尾的位置、大小与鱼尾形状。",
            "不额外增加四肢、道具或配件，除非动作明确要求。",
            "走路帧固定侧视、固定画布、固定角色比例和固定脚底基线。",
            "不使用文字、角标、水印、背景、投影或运动模糊。",
        ],
        "runtime_policy": {
            "art_family": "unified_generated_v1",
            "user_authorized_generated_assets": True,
            "paid_pose_images": "motion_reference_only_not_runtime_art",
            "walking_status": "formal_four_frame_cycle",
            "runtime_ai": False,
        },
    }


def action(
    action_id: str,
    asset: str,
    motion: str,
    duration_ms: int | None,
    priority: int,
    *,
    loop: bool = False,
    interruptible: bool = True,
    return_state: str = "IDLE",
    anchor_type: str = "ground",
    quality: str = "formal_unified_generated_action",
    requires_real_frames: bool = False,
) -> dict[str, Any]:
    return {
        "id": action_id,
        "asset": asset,
        "loop": loop,
        "duration_ms": duration_ms,
        "priority": priority,
        "interruptible": interruptible,
        "return_state": return_state,
        "anchor": {
            "type": anchor_type,
            "x": 0.5,
            "y": 0.96 if anchor_type == "ground" else 0.5,
        },
        "procedural_motion": {"type": motion},
        "quality": quality,
        "requires_real_frames": requires_real_frames,
    }


def _asset_quality(runtime_assets: dict[str, Any], asset_id: str, fallback: str) -> str:
    raw = runtime_assets.get(asset_id, {})
    return str(raw.get("quality", fallback)) if isinstance(raw, dict) else fallback


def actions_manifest(runtime_assets: dict[str, Any]) -> dict[str, Any]:
    quality = lambda asset, fallback="formal_unified_generated_action": _asset_quality(runtime_assets, asset, fallback)
    actions = [
        action("IDLE", "idle_front", "breath", None, 10, loop=True, quality=quality("idle_front", "clean_base_view")),
        action("THINKING", "idle_think", "think", 2400, 20, quality=quality("idle_think")),
        action(
            "WALKING",
            "walk_side",
            "walk_frames",
            None,
            30,
            loop=True,
            quality=quality("walk_side", "formal_unified_generated_walk_frames"),
        ),
        action("HAPPY", "happy", "bounce", 1050, 60, quality=quality("happy")),
        action("TALKING", "talk", "talk", 2900, 45, quality=quality("talk")),
        action("ANGRY", "angry", "angry", 1500, 70, interruptible=False, quality=quality("angry")),
        action("POKE_REACT", "poke_react", "recoil", 430, 80, interruptible=False, quality=quality("poke_react")),
        action("EATING", "eat", "eat", 1500, 65, interruptible=False, quality=quality("eat")),
        action("SWEEPING", "sweep", "sweep", 2800, 25, quality=quality("sweep")),
        action(
            "SLEEPING",
            "sleep",
            "sleep",
            None,
            35,
            loop=True,
            interruptible=True,
            anchor_type="sleep",
            quality=quality("sleep"),
        ),
        action(
            "DRAGGING",
            "dragging",
            "float",
            None,
            100,
            loop=True,
            interruptible=False,
            anchor_type="drag",
            quality=quality("dragging"),
        ),
        action(
            "FALLING",
            "falling",
            "fall",
            900,
            90,
            interruptible=False,
            anchor_type="drag",
            quality=quality("falling"),
        ),
        action(
            "DIZZY",
            "dizzy",
            "dizzy",
            2100,
            75,
            interruptible=False,
            anchor_type="seat",
            quality=quality("dizzy"),
        ),
    ]
    return {
        "format_version": 2,
        "character_id": "dafeiyu",
        "assets": runtime_assets,
        "actions": {entry["id"]: entry for entry in actions},
        "fallbacks": {
            "walk_side": "idle_front",
            "talk": "idle_front",
            "sleep": "idle_front",
            "dragging": "idle_front",
            "dizzy": "idle_front",
        },
        "notes": [
            "所有运行时动作均来自同一套统一角色母版；运行时不生成图片。",
            "WALKING 是已接入的四帧侧视循环，而非程序化滑行 placeholder。",
            "用户提供的付费状态图仅作为动作语义参考，不混入最终显示图集。",
        ],
    }


def write_character_doc(spec: dict[str, Any], output: Path) -> None:
    lines = [
        "# 大肥鱼角色一致性规范",
        "",
        "运行时动作图统一来自同一套绿幕角色母版；正、侧、背三视图用于校准方向和不可变识别元素。用户提供的付费姿势图只用于学习动作语义，不混入显示图集。",
        "",
        "## 角色识别要点",
        "",
    ]
    for key, value in spec["visual_language"].items():
        lines.append(f"- **{key}**：{value}")
    lines.extend(["", "## 不可改变项", ""])
    lines.extend(f"- {item}" for item in spec["non_negotiable_invariants"])
    lines.extend(["", "## 运行时约束", ""])
    lines.extend(f"- **{key}**：{value}" for key, value in spec["runtime_policy"].items())
    lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def write_architecture_doc(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        """# 动画系统架构

## 目标

动画、素材选择、状态转换和窗口移动分离。运行时只加载预生成 PNG 与 PySide6 `QPixmap`，不运行图像模型、不截图、不访问网络。

## 模块

- `animation.asset_registry`：读取 `actions.json`，按桌宠尺寸缓存 `QPixmap`。
- `animation.clip`：定义 clip、frame、锚点与动作请求的数据结构。
- `animation.player`：推进帧时间、处理交叉淡化，输出当前与上一张精灵图。
- `animation.effects`：参数化轻微呼吸、思考摇摆、真实行走帧播放、反冲、弹跳、进食、眩晕等效果。
- `animation.state_machine`：处理动作优先级、中断、有限动作超时返回与拖拽强制中断。
- `animation.transitions`：封装不闪烁的交叉淡化。

## 状态

`IDLE`、`THINKING`、`WALKING`、`HAPPY`、`TALKING`、`ANGRY`、`POKE_REACT`、`EATING`、`SWEEPING`、`SLEEPING`、`DRAGGING`、`FALLING`、`DIZZY`。

`WALKING` 现为正式四帧侧面循环。它通过四张独立的接地/经过/反向接地/抬步帧在 8 FPS 左右循环，向右时由运行时镜像；程序化效果只做极轻微的重心补充，不再把整张侧面立绘平移冒充走路。

## 锚点

站立状态以脚底中点为 ground anchor；睡眠、眩晕、拖拽与掉落均使用独立非地面锚点。渲染时会把这些状态置于精灵槽中央，因此抓取不会再只露出脑袋，睡姿也不会被强压到地面基线。
""",
        encoding="utf-8",
    )


def write_walk_request(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        """# 侧面走路素材状态

当前已接入正式四帧侧视走路循环，来源为用户认可的统一绿幕角色图集：`assets/candidates/walk_side/candidate_a/`。运行时文件位于 `assets/processed/runtime/states/walk_side/`，8 FPS 预览位于 `assets/previews/gifs/walk_side_candidate_a_8fps.gif`。

四帧分别覆盖接地、经过、反向接地和抬步；所有帧在归一化时共享画布、比例和脚底基线。左向使用原始左向帧，右向由运行时镜像。后续若请画师精修，应保持这一组的角色身份和四帧节奏，不是当前版本的阻塞项。
""",
        encoding="utf-8",
    )


def write_processing_report(runtime: dict[str, Any], output: Path) -> None:
    assets = runtime.get("assets", {})
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 素材处理报告",
        "",
        "## 当前运行时美术策略",
        "",
        "正式显示素材统一采用同一套生成角色母版。它以干净三视图为身份校准，并用统一绿幕动作表补齐表情、互动与走路。用户提供的付费状态图保留在原始素材目录，仅用于动作语义参考；没有被裁入、混入或覆盖到运行时图集中。",
        "",
        "## 已处理的运行时资产",
        "",
    ]
    for state, item in assets.items():
        if not isinstance(item, dict):
            continue
        masters = ", ".join(str(value) for value in item.get("source_masters", []))
        lines.append(
            f"- `{state}`：{item.get('quality', 'unknown')}，{item.get('frame_count', 0)} 帧，来源 `{masters}`"
        )
    lines.extend(
        [
            "",
            "## 提取与规范化",
            "",
            "- 绿色键控背景在资产制作阶段去除，输出为透明 PNG；运行时不加载图像模型。",
            "- 走路四帧共享缩放比例、透明画布和脚底基线。",
            "- 睡眠、眩晕、抓取和掉落使用各自的视觉尺度与锚点，不强行拉成站立高度。",
            "- 单独悬浮的提示符号会在键控后作为非主体透明岛剔除；角色本体不做内容重绘。",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    manifests = PROJECT_ROOT / "assets" / "manifests"
    docs = PROJECT_ROOT / "docs"
    runtime = load_json(manifests / "runtime_inventory.json", {"assets": {}})
    spec = character_spec()
    manifests.mkdir(parents=True, exist_ok=True)
    (manifests / "character_spec.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    actions = actions_manifest(runtime.get("assets", {}))
    (manifests / "actions.json").write_text(
        json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_character_doc(spec, docs / "CHARACTER_SPEC.md")
    write_architecture_doc(docs / "ANIMATION_ARCHITECTURE.md")
    write_walk_request(docs / "WALK_ASSET_REQUEST.md")
    write_processing_report(runtime, docs / "ASSET_PROCESSING_REPORT.md")
    print("写入统一角色的 manifest 与动画文档")


if __name__ == "__main__":
    main()
