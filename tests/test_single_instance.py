from __future__ import annotations

import time
import unittest
import uuid

from PySide6.QtCore import QCoreApplication

from app.single_instance import SingleInstance


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QCoreApplication.instance() or QCoreApplication([])

    def test_repeat_launch_notifies_existing_instance(self) -> None:
        name = f"dafeiyu-test-{uuid.uuid4().hex}"
        activations: list[bool] = []
        primary = SingleInstance(name)
        try:
            self.assertTrue(primary.acquire())
            primary.set_activation_handler(lambda: activations.append(True))
            repeated = SingleInstance(name)
            self.assertFalse(repeated.acquire())

            deadline = time.monotonic() + 1.0
            while not activations and time.monotonic() < deadline:
                self.application.processEvents()
                time.sleep(0.01)
            self.assertEqual(activations, [True])
        finally:
            primary.close()
