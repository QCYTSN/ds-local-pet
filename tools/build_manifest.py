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
    transition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
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
    if transition:
        entry["transition"] = transition
    return entry


def _asset_quality(runtime_assets: dict[str, Any], asset_id: str, fallback: str) -> str:
    raw = runtime_assets.get(asset_id, {})
    return str(raw.get("quality", fallback)) if isinstance(raw, dict) else fallback


def actions_manifest(runtime_assets: dict[str, Any]) -> dict[str, Any]:
    quality = lambda asset, fallback="formal_unified_generated_action": _asset_quality(runtime_assets, asset, fallback)
    actions = [
        action(
            "IDLE",
            "idle_front",
            "breath",
            None,
            10,
            loop=True,
            quality=quality("idle_front", "formal_unified_generated_idle_base"),
        ),
        action(
            "BLINK",
            "idle_blink",
            "micro_idle",
            560,
            12,
            quality=quality("idle_blink", "formal_unified_generated_micro_frames"),
        ),
        action(
            "GLANCE",
            "idle_glance",
            "micro_idle",
            1260,
            12,
            quality=quality("idle_glance", "formal_unified_generated_micro_frames"),
        ),
        action("THINKING", "idle_think", "think", 2400, 20, quality=quality("idle_think")),
        action(
            "WALKING",
            "walk_side",
            "walk_frames",
            None,
            30,
            loop=True,
            quality=quality("walk_side", "formal_unified_generated_walk_frames"),
            transition={
                "enter": {
                    "asset": "walk_start_left",
                    "duration_ms": 260,
                    "effect": "walk_start",
                },
                "exit": {
                    "asset": "walk_stop_left",
                    "duration_ms": 300,
                    "effect": "walk_stop",
                },
            },
        ),
        action("HAPPY", "happy", "bounce", 1050, 60, quality=quality("happy")),
        action(
            "HEAD_PAT",
            "head_pat",
            "head_pat",
            1200,
            68,
            interruptible=False,
            quality=quality("head_pat", "formal_unified_generated_interaction_frames"),
        ),
        action("TALKING", "talk", "talk", 2900, 45, quality=quality("talk")),
        action("ANGRY", "angry", "angry", 1500, 70, interruptible=False, quality=quality("angry")),
        action("POKE_REACT", "poke_react", "poke_frames", 760, 80, interruptible=False, quality=quality("poke_react")),
        action("TAIL_REACT", "tail_react", "tail_react", 980, 82, interruptible=False, quality=quality("tail_react")),
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
            transition={
                "enter": {
                    "asset": "sleep_enter",
                    "duration_ms": 1050,
                    "effect": "sleep_enter",
                },
                "exit": {
                    "asset": "sleep_wake",
                    "duration_ms": 900,
                    "effect": "sleep_wake",
                },
            },
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
            None,
            90,
            loop=True,
            interruptible=False,
            anchor_type="drag",
            quality=quality("falling"),
            transition={
                "enter": {
                    "asset": "released_airborne",
                    "duration_ms": 140,
                    "effect": "fall",
                }
            },
        ),
        action(
            "LANDING",
            "landing",
            "landing",
            620,
            85,
            interruptible=False,
            anchor_type="ground",
            quality=quality("landing", "formal_unified_generated_landing_frames"),
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
        "format_version": 4,
        "character_id": "dafeiyu",
        "assets": runtime_assets,
        "actions": {entry["id"]: entry for entry in actions},
        "fallbacks": {
            "idle_blink": "idle_front",
            "idle_glance": "idle_front",
            "head_pat": "happy",
            "walk_side": "idle_front",
            "walk_side_right": "walk_side",
            "walk_start_left": "walk_side_stand",
            "walk_start_right": "walk_side_stand",
            "walk_stop_left": "walk_side_stand",
            "walk_stop_right": "walk_side_stand",
            "talk": "idle_front",
            "sleep": "idle_front",
            "dragging": "idle_front",
            "released_airborne": "falling",
            "landing": "dizzy",
            "dizzy": "idle_front",
            "tail_react": "poke_react",
        },
        "notes": [
            "所有运行时动作均来自同一套统一角色母版；运行时不生成图片。",
            "WALKING 使用独立左右四帧循环与起步/刹停过渡，而非镜像滑行 placeholder。",
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

动画、素材选择、状态转换和窗口移动分离。动作系统只加载预生成 PNG 与 PySide6 `QPixmap`，不运行图像模型、不截图；联网仅由独立、可关闭的版本检查器负责。

## 模块

- `animation.asset_registry`：读取 `actions.json`，按桌宠尺寸缓存 `QPixmap`。
- `animation.clip`：定义 clip、frame、锚点，以及 enter/body/exit 动作协议。
- `animation.player`：推进动作分段与帧时间、处理安全的同素材淡化，输出当前精灵图。
- `animation.effects`：参数化轻微呼吸、思考摇摆、真实行走帧播放、反冲、弹跳、进食、眩晕等效果。
- `animation.state_machine`：处理动作优先级、中断、有限动作超时返回与拖拽强制中断。
- `animation.transitions`：封装不闪烁的交叉淡化。
- `pet.physics`：独立处理抛掷速度、重力、屏幕/窗口表面碰撞、反弹、摩擦与落地判定。
- `pet.surfaces`：只读取窗口矩形，管理窗口顶部平台、落脚附着、窗口随动和表面行走边界。

## 状态

`IDLE`、`BLINK`、`GLANCE`、`THINKING`、`WALKING`、`HAPPY`、`HEAD_PAT`、`TALKING`、`ANGRY`、`POKE_REACT`、`TAIL_REACT`、`EATING`、`SWEEPING`、`SLEEPING`、`DRAGGING`、`FALLING`、`LANDING`、`DIZZY`。

`WALKING` 现为正式左右双套四帧侧面循环。每个方向都有接地/经过/反向接地/抬步帧，并在进入和退出时播放独立起步、刹停过渡；右向不再镜像左向，蝴蝶结、围裙图案和发饰保持解剖位置。

`BLINK`、`GLANCE` 由独立微动作调度器触发，不计作一次完整活动；`HEAD_PAT` 与 `POKE_REACT` 使用连续实帧表达互动过程。完整活动默认间隔显著拉长，主动说话另有长冷却，避免桌宠常驻时显得忙乱。

自动散步只改变水平坐标并保持当前表面脚底基线。拖拽释放后才转交给 `ThrowPhysics` 改变纵向坐标；轻落地播放压身恢复，重摔在落地动作后进入眩晕。普通窗口顶部会作为单向水平平台接住从上方落下的角色；落脚后按相对位置随窗口移动，窗口消失时重新交给重力。快速横甩会在工作区边缘减速反弹，速度和单帧积分均有限制。

## 锚点

站立状态以脚底中点为 ground anchor；睡眠、眩晕、拖拽与掉落均使用独立非地面锚点。渲染时会把这些状态置于精灵槽中央，因此抓取不会再只露出脑袋，睡姿也不会被强压到地面基线。
""",
        encoding="utf-8",
    )


def write_walk_request(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        """# 侧面走路素材状态

当前已接入左右独立的正式四帧侧视走路循环。左向来源为 `assets/candidates/walk_side/candidate_a/`，右向与起停过渡位于 `assets/candidates/state_actions/candidate_g_motion2/`。运行时文件位于 `assets/processed/runtime/states/walk_side*`。

四帧分别覆盖接地、经过、反向接地和抬步；所有帧在归一化时共享画布、比例和脚底基线。左右向各自保留固定配饰位置，并通过两帧起步与两帧刹停动作衔接待机。
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
