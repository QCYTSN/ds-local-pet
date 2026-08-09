from __future__ import annotations

import unittest

from pet.movement import MovementController
from pet.physics import PhysicsBounds, PhysicsPlatform, ThrowPhysics


class FakeWidget:
    def __init__(self, x: int = 100, y: int = 240) -> None:
        self._x = x
        self._y = y

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def move(self, x: int, y: int) -> None:
        self._x = x
        self._y = y


class ThrowPhysicsTests(unittest.TestCase):
    def test_launch_velocity_is_limited_without_changing_direction(self) -> None:
        physics = ThrowPhysics(max_launch_speed=1000.0)
        physics.launch(0, 0, 3000, 4000)
        self.assertAlmostEqual(physics.speed, 1000.0)
        self.assertAlmostEqual(physics.velocity_x / physics.velocity_y, 0.75)

    def test_fast_fall_bounces_then_reports_hard_landing(self) -> None:
        physics = ThrowPhysics()
        bounds = PhysicsBounds(0, 0, 1200, 900)
        physics.launch(220, 20, 180, 0)
        result = None
        saw_impact = False
        for _ in range(300):
            result = physics.step(0.02, width=180, height=260, bounds=bounds)
            saw_impact = saw_impact or result.first_impact
            if result.settled:
                break
        self.assertIsNotNone(result)
        self.assertTrue(saw_impact)
        self.assertTrue(result.settled)
        self.assertTrue(result.hard_landing)
        self.assertEqual(result.y, bounds.bottom - 260 + 1)

    def test_horizontal_throw_rebounds_from_work_area_edge(self) -> None:
        physics = ThrowPhysics()
        bounds = PhysicsBounds(0, 0, 500, 700)
        physics.launch(390, 80, 1200, -100)
        result = physics.step(0.04, width=100, height=180, bounds=bounds)
        self.assertLess(result.velocity_x, 0.0)
        self.assertLessEqual(result.x, 401.0)

    def test_gentle_release_near_floor_settles_without_dizzy(self) -> None:
        physics = ThrowPhysics()
        bounds = PhysicsBounds(0, 0, 800, 600)
        floor_y = bounds.bottom - 180 + 1
        physics.launch(200, floor_y - 2, 20, 0)
        result = physics.step(0.08, width=120, height=180, bounds=bounds)
        self.assertTrue(result.settled)
        self.assertFalse(result.hard_landing)

    def test_descending_pet_can_land_on_a_window_top_platform(self) -> None:
        physics = ThrowPhysics()
        platform = PhysicsPlatform(180, 620, 430, "window:42")
        bounds = PhysicsBounds(0, 0, 900, 800, platforms=(platform,))
        physics.launch(280, 120, 0, 0)

        result = None
        for _ in range(300):
            result = physics.step(0.02, width=140, height=180, bounds=bounds)
            if result.settled:
                break

        self.assertIsNotNone(result)
        self.assertTrue(result.settled)
        self.assertEqual(result.landed_surface_id, "window:42")
        self.assertEqual(result.y, platform.top - 180)


class GroundMovementTests(unittest.TestCase):
    def test_walking_changes_x_but_never_changes_ground_y(self) -> None:
        widget = FakeWidget()
        movement = MovementController(speed=80.0)
        movement.target = (240.0, -500.0)
        directions: list[str] = []
        walking = movement.update(
            widget,  # type: ignore[arg-type]
            now=1.0,
            delta_seconds=0.1,
            set_direction=lambda direction, _facing: directions.append(direction),
        )
        self.assertTrue(walking)
        self.assertGreater(widget.x(), 100)
        self.assertEqual(widget.y(), 240)
        self.assertEqual(directions[-1], "right")


if __name__ == "__main__":
    unittest.main()
