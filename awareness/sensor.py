from __future__ import annotations

import os
import time
from collections.abc import Iterable

from awareness.active_window import ActiveWindowReader
from awareness.context_snapshot import ContextSnapshot
from awareness.fullscreen_detector import FullscreenDetector
from awareness.idle_detector import IdleDetector
from awareness.privacy import PrivacyPolicy
from behavior.classifier import AppClassifier


class ContextSensor:
    """Combines low-cost Windows metadata into one local context snapshot."""

    def __init__(
        self,
        classifier: AppClassifier,
        privacy_policy: PrivacyPolicy,
        *,
        ignored_pids: Iterable[int] = (),
    ) -> None:
        self._reader = ActiveWindowReader()
        self._idle_detector = IdleDetector()
        self._fullscreen_detector = FullscreenDetector()
        self._classifier = classifier
        self._privacy_policy = privacy_policy
        self._ignored_pids = {os.getpid(), *ignored_pids}

    def capture(
        self,
        *,
        read_window_title: bool,
        idle_detection: bool,
        custom_private_process_names: Iterable[str] = (),
    ) -> ContextSnapshot | None:
        window = self._reader.read()
        if window is None or window.pid in self._ignored_pids:
            return None
        raw_title = window.title
        is_private = self._privacy_policy.is_private(
            window.process_name,
            raw_title,
            custom_private_process_names,
        )
        category = self._classifier.classify(window.process_name, raw_title)
        return ContextSnapshot(
            timestamp=time.time(),
            process_name=window.process_name,
            window_title="" if is_private or not read_window_title else raw_title,
            pid=window.pid,
            idle_seconds=self._idle_detector.seconds() if idle_detection else 0.0,
            is_fullscreen=self._fullscreen_detector.is_fullscreen(window.handle),
            category=category,
            window_handle=window.handle,
            is_private=is_private,
        )
