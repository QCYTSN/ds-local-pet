"""Manifest-backed QPixmap registry with size selection and asset fallback."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QPixmap

from .clip import ActionSpec, Anchor, AnimationClip, ClipFrame, PetAction


class AssetRegistry:
    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = Path(assets_dir)
        self.project_root = self.assets_dir.parent
        manifest_path = self.assets_dir / "manifests" / "actions.json"
        self.manifest_path = manifest_path
        try:
            self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as error:
            raise RuntimeError(f"无法读取动作清单：{manifest_path}") from error
        self._assets = self.manifest.get("assets", {})
        self.specs = self._parse_specs()
        self._frame_cache: dict[tuple[str, int], tuple[ClipFrame, ...]] = {}

    def _parse_specs(self) -> dict[PetAction, ActionSpec]:
        raw_actions = self.manifest.get("actions", {})
        specs: dict[PetAction, ActionSpec] = {}
        for raw_name, raw in raw_actions.items():
            if not isinstance(raw, dict):
                continue
            action = PetAction.coerce(raw.get("id", raw_name))
            anchor_raw = raw.get("anchor", {})
            if not isinstance(anchor_raw, dict):
                anchor_raw = {}
            specs[action] = ActionSpec(
                action=action,
                asset_id=str(raw["asset"]),
                loop=bool(raw.get("loop", False)),
                duration_ms=raw.get("duration_ms") if isinstance(raw.get("duration_ms"), int) else None,
                priority=int(raw.get("priority", 0)),
                interruptible=bool(raw.get("interruptible", True)),
                return_state=PetAction.coerce(raw.get("return_state", "IDLE")),
                anchor=Anchor(
                    kind=str(anchor_raw.get("type", "ground")),
                    x=float(anchor_raw.get("x", 0.5)),
                    y=float(anchor_raw.get("y", 0.985)),
                ),
                effect=str((raw.get("procedural_motion") or {}).get("type", "breath")),
                quality=str(raw.get("quality", "placeholder")),
                requires_real_frames=bool(raw.get("requires_real_frames", False)),
            )
        return specs

    def clip_for(self, action: PetAction | str, *, height: int, direction: str) -> AnimationClip:
        action = PetAction.coerce(action)
        spec = self.specs[action]
        asset_id = self._asset_for(action, spec.asset_id, direction)
        frames, selected_size = self._frames_for(asset_id, height)
        frame_duration = self._frame_duration_ms(spec, len(frames))
        return AnimationClip(
            action=action,
            asset_id=asset_id,
            frames=frames,
            loop=spec.loop,
            duration_ms=spec.duration_ms,
            frame_duration_ms=frame_duration,
            anchor=spec.anchor,
            effect=spec.effect,
            quality=spec.quality,
            requires_real_frames=spec.requires_real_frames,
            # The supplied side master faces left; mirror only when moving right.
            mirrored=asset_id.startswith("walk_side") and direction == "right",
        )

    @staticmethod
    def _asset_for(action: PetAction, default_asset: str, direction: str) -> str:
        if action in {PetAction.IDLE, PetAction.THINKING}:
            return "idle_back" if direction == "up" else ("idle_think" if action == PetAction.THINKING else "idle_front")
        if action == PetAction.WALKING and direction == "up":
            return "idle_back"
        if action == PetAction.WALKING and direction == "down":
            return "idle_front"
        return default_asset

    def _frames_for(self, asset_id: str, height: int) -> tuple[tuple[ClipFrame, ...], int]:
        raw_asset = self._assets.get(asset_id)
        if not isinstance(raw_asset, dict):
            raise RuntimeError(f"动作清单缺少素材：{asset_id}")
        frames_by_size = raw_asset.get("frames", {})
        available = sorted(int(size) for size in frames_by_size if str(size).isdigit())
        if not available:
            raise RuntimeError(f"素材 {asset_id} 没有尺寸帧")
        selected_size = min(available, key=lambda size: abs(size - height))
        cache_key = (asset_id, selected_size)
        if cache_key not in self._frame_cache:
            raw_paths = frames_by_size[str(selected_size)]
            loaded: list[ClipFrame] = []
            for raw_path in raw_paths:
                path = self.project_root / str(raw_path)
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    raise RuntimeError(f"无法加载动作帧：{path}")
                loaded.append(ClipFrame(path, pixmap))
            self._frame_cache[cache_key] = tuple(loaded)
        return self._frame_cache[cache_key], selected_size

    @staticmethod
    def _frame_duration_ms(spec: ActionSpec, frame_count: int) -> int:
        if frame_count <= 0:
            return 120
        if spec.duration_ms is not None:
            return max(70, spec.duration_ms // frame_count)
        return 120 if spec.action == PetAction.WALKING else 180
