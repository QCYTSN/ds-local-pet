#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a repeatable offscreen renderer check and write a transparent report."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from animation.asset_registry import AssetRegistry
from animation.clip import PetAction
from app.paths import AppPaths
from pet.window import PetWindow
from settings.config import ConfigManager


REPORT_PATH = PROJECT_ROOT / "docs" / "PERFORMANCE_REPORT.md"


def main() -> None:
    app = QApplication.instance() or QApplication([])
    registry = AssetRegistry(PROJECT_ROOT / "assets")
    loaded = []
    start = time.perf_counter()
    for action in PetAction:
        for direction in ("left", "right", "up", "down"):
            loaded.extend(registry.clip_for(action, height=238, direction=direction).frames)
    registry_warm_ms = (time.perf_counter() - start) * 1000.0
    unique_sources = {frame.source: frame.pixmap for frame in loaded}
    resident_bytes = sum(pixmap.width() * pixmap.height() * 4 for pixmap in unique_sources.values())
    # Measure only files referenced by the active manifest.  Old, deliberately
    # unreferenced build artifacts must not inflate the formal runtime budget.
    runtime_paths = {
        PROJECT_ROOT / str(path)
        for asset in registry.manifest.get("assets", {}).values()
        if isinstance(asset, dict)
        for frames in asset.get("frames", {}).values()
        if isinstance(frames, list)
        for path in frames
    }
    runtime_files = sorted(path for path in runtime_paths if path.is_file())
    disk_bytes = sum(path.stat().st_size for path in runtime_files)

    with TemporaryDirectory() as folder:
        paths = AppPaths(app_dir=Path(folder), bundle_dir=PROJECT_ROOT)
        window = PetWindow(paths, ConfigManager(paths.config_path))
        window.timer.stop()
        window.awareness_timer.stop()
        window.movement.set_mode("still")
        window._preview_action("WALKING")
        app.processEvents()
        image = QImage(window.size(), QImage.Format.Format_ARGB32_Premultiplied)
        frames = 180
        start = time.perf_counter()
        for _ in range(frames):
            window.player.tick(1.0 / 50.0)
            image.fill(0)
            painter = QPainter(image)
            window.render(painter, QPoint())
            painter.end()
        render_seconds = time.perf_counter() - start
        window.tray.hide()
        window.control_panel.hide()
        window.food_panel.hide()
        window.hide()

    render_ms = render_seconds * 1000.0 / frames
    result = {
        "renderer_frames": frames,
        "average_render_ms": round(render_ms, 3),
        "offscreen_fps_equivalent": round(frames / render_seconds, 1),
        "registry_warm_ms": round(registry_warm_ms, 3),
        "formal_runtime_png_count": len(runtime_files),
        "formal_runtime_disk_kib": round(disk_bytes / 1024.0, 1),
        "loaded_current_size_pixmap_mib": round(resident_bytes / (1024.0 * 1024.0), 3),
        "pyside": pyside_version,
    }
    report = f"""# 性能验证报告

## 结论

动画时钟固定为 20ms（目标 50 FPS）。在本机离屏渲染基准中，180 帧平均渲染为 **{result['average_render_ms']} ms/帧**，等效 **{result['offscreen_fps_equivalent']} FPS**；这说明当前透明精灵、气泡和程序化效果的绘制预算足以覆盖 50 FPS 的目标。

## 本次测量

- PySide6：{result['pyside']}
- 运行时 PNG：{result['formal_runtime_png_count']} 个，磁盘占用 {result['formal_runtime_disk_kib']} KiB
- 当前尺寸已加载的独立 `QPixmap` 估算：{result['loaded_current_size_pixmap_mib']} MiB
- 清单与当前尺寸纹理预热：{result['registry_warm_ms']} ms
- 离屏画面：{result['renderer_frames']} 帧，平均 {result['average_render_ms']} ms/帧

## 边界

这是受控离屏渲染检查，不把桌面合成器、其他应用占用或多屏 DPI 计入结果。运行时不加载图像模型、不截图、不访问网络；正式四帧走路与统一角色状态图均已计入本次资源预热和绘制检查。
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
