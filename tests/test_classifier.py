from __future__ import annotations

import unittest
from pathlib import Path

from awareness.privacy import PrivacyPolicy
from behavior.classifier import AppClassifier


ASSETS = Path(__file__).resolve().parents[1] / "assets"


class AppClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = AppClassifier(ASSETS / "app_categories.json")

    def test_executable_name_wins_for_coding_apps(self) -> None:
        self.assertEqual(
            self.classifier.classify("Code.exe", "my-github-project - Visual Studio Code"),
            "coding",
        )

    def test_browser_titles_refine_the_category(self) -> None:
        self.assertEqual(
            self.classifier.classify("msedge.exe", "1190fasheqi/dafeiyu-pet - GitHub"),
            "github",
        )
        self.assertEqual(
            self.classifier.classify("chrome.exe", "DeepSeek - 问答"),
            "ai_chat",
        )
        self.assertEqual(
            self.classifier.classify("firefox.exe", "哔哩哔哩 (゜-゜)つロ 干杯~"),
            "video",
        )

    def test_documents_and_unknown_apps_have_safe_fallbacks(self) -> None:
        self.assertEqual(
            self.classifier.classify("Acrobat.exe", "paper.pdf"),
            "document",
        )
        self.assertEqual(self.classifier.classify("something.exe", "Untitled"), "unknown")


class PrivacyPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = PrivacyPolicy(ASSETS / "privacy_rules.json")

    def test_sensitive_processes_and_private_windows_are_suppressed(self) -> None:
        self.assertTrue(self.policy.is_private("WeChat.exe", "朋友聊天"))
        self.assertTrue(self.policy.is_private("msedge.exe", "InPrivate - Microsoft Edge"))
        self.assertTrue(
            self.policy.is_private(
                "internal-tool.exe",
                "anything",
                custom_process_names=["internal-tool.exe"],
            )
        )

    def test_regular_editor_is_not_suppressed(self) -> None:
        self.assertFalse(self.policy.is_private("Code.exe", "pet/window.py"))
