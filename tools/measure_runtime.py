# -*- coding: utf-8 -*-
"""Record CPU and memory for a running desktop-pet process without profiling data."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import psutil


def main() -> None:
    parser = argparse.ArgumentParser(description="采样一个已运行进程的 CPU 与内存占用。")
    parser.add_argument("--pid", required=True, type=int, help="桌宠进程的 PID。")
    parser.add_argument("--seconds", type=float, default=60.0, help="采样时长，默认 60 秒。")
    parser.add_argument(
        "--output",
        type=Path,
        help="可选：把 JSON 结果写入这个文件。",
    )
    arguments = parser.parse_args()
    if arguments.seconds <= 0:
        parser.error("--seconds 必须为正数。")

    try:
        process = psutil.Process(arguments.pid)
        starting_cpu = process.cpu_times()
        starting_memory = process.memory_info().rss
    except psutil.Error as error:
        parser.error(f"无法读取 PID {arguments.pid}：{error}")

    started_at = time.monotonic()
    peak_memory = starting_memory
    while time.monotonic() - started_at < arguments.seconds:
        time.sleep(min(0.5, arguments.seconds))
        try:
            peak_memory = max(peak_memory, process.memory_info().rss)
        except psutil.Error as error:
            parser.error(f"采样过程中进程已退出：{error}")

    elapsed = time.monotonic() - started_at
    ending_cpu = process.cpu_times()
    ending_memory = process.memory_info().rss
    cpu_seconds = (ending_cpu.user - starting_cpu.user) + (
        ending_cpu.system - starting_cpu.system
    )
    result = {
        "pid": arguments.pid,
        "process": process.name(),
        "duration_seconds": round(elapsed, 2),
        "mean_cpu_percent": round(cpu_seconds / elapsed * 100, 3),
        "rss_mb_start": round(starting_memory / 1024 / 1024, 2),
        "rss_mb_end": round(ending_memory / 1024 / 1024, 2),
        "rss_mb_peak": round(peak_memory / 1024 / 1024, 2),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
