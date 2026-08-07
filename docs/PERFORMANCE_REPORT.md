# Performance Verification Report

## Summary

The animation clock runs at a fixed 20 ms interval (target 50 FPS). In an off-screen rendering benchmark, the average draw time per frame is **0.18 ms**, which occupies **0.9%** of the 20 ms per-frame budget. This leaves ample headroom for the transparent sprite, bubble, and programmatic effects.

## Measured Values

| Metric | Value |
|--------|-------|
| PySide6 version | 6.11.1 |
| Runtime PNG files | 51, ~3.9 MiB on disk |
| Loaded QPixmap memory (estimate) | 3.1 MiB |
| Manifest + texture warm-up | 22.6 ms |
| Off-screen benchmark: 180 frames | 0.18 ms/frame average |
| **Implied draw budget usage** | **0.9% at target 50 FPS** |

## Caveats

- This is a controlled off-screen rendering benchmark. It does **not** include the desktop compositor, other applications, or multi-monitor DPI scaling.
- The runtime does not load image models, take screenshots, or access the network.
- The formal 4-frame walk cycle and all unified character state assets are included in the resource warm-up and draw time measurement.
- **This is NOT equivalent to real-world desktop FPS.** The off-screen draw time is a lower bound; actual on-screen performance depends on GPU composition, display refresh rate, and system load.

## Real-World Performance (Windows)

To be measured on actual Windows hardware. Recommended measurement points:

- **Idle CPU**: pet visible but not animating
- **Walking CPU**: continuous walking animation
- **RSS memory**: after startup, after 1 hour
- **Startup time**: from double-click to visible pet
- **Memory growth**: check for leaks over 4+ hours

These measurements require a dedicated Windows test environment and are not yet available automatically.