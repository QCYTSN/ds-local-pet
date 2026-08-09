from __future__ import annotations

import unittest

from pet.interaction import InteractionController


class InteractionRegionTests(unittest.TestCase):
    def classify(self, x: float, y: float) -> str:
        return InteractionController.classify_region(x, y, 0.0, 0.0, 100.0, 100.0)

    def test_face_head_tail_and_body_have_distinct_hit_regions(self) -> None:
        self.assertEqual(self.classify(50, 30), "face")
        self.assertEqual(self.classify(20, 15), "head")
        self.assertEqual(self.classify(82, 66), "tail")
        self.assertEqual(self.classify(50, 70), "body")

    def test_points_outside_character_bounds_fall_back_to_body(self) -> None:
        self.assertEqual(self.classify(-4, 50), "body")
        self.assertEqual(
            InteractionController.classify_region(1, 1, 0, 0, 0, 100),
            "body",
        )


if __name__ == "__main__":
    unittest.main()
