from __future__ import annotations

import json
import unittest
from pathlib import Path

from animation.asset_registry import AssetRegistry
from animation.clip import ActionSpec, Anchor, AnimationClip, ClipFrame, PetAction
from animation.player import AnimationPlayer
from animation.state_machine import ActionStateMachine


def make_specs() -> dict[PetAction, ActionSpec]:
    specs: dict[PetAction, ActionSpec] = {}
    for action in PetAction:
        specs[action] = ActionSpec(
            action=action,
            asset_id=action.value.lower(),
            loop=action in {PetAction.IDLE, PetAction.WALKING, PetAction.DRAGGING},
            duration_ms=None if action in {PetAction.IDLE, PetAction.WALKING, PetAction.DRAGGING} else 100,
            priority={
                PetAction.IDLE: 10,
                PetAction.WALKING: 30,
                PetAction.POKE_REACT: 80,
                PetAction.FALLING: 90,
                PetAction.DRAGGING: 100,
            }.get(action, 40),
            interruptible=action not in {PetAction.POKE_REACT, PetAction.FALLING, PetAction.DRAGGING},
            return_state=PetAction.IDLE,
            anchor=Anchor(),
            effect="breath",
            quality="source",
            requires_real_frames=False,
        )
    return specs


class ActionStateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.machine = ActionStateMachine(make_specs())

    def test_non_interruptible_poke_blocks_walking(self) -> None:
        self.assertIsNotNone(
            self.machine.request(PetAction.POKE_REACT, now=1.0, reason="tap")
        )
        self.assertIsNone(
            self.machine.request(PetAction.WALKING, now=1.01, reason="movement")
        )
        self.assertEqual(self.machine.current, PetAction.POKE_REACT)

    def test_falling_can_queue_dizzy(self) -> None:
        self.machine.request(PetAction.FALLING, now=1.0, reason="throw", force=True)
        self.machine.queue_after_current(PetAction.DIZZY)
        change = self.machine.update(now=1.11)
        self.assertIsNotNone(change)
        self.assertEqual(self.machine.current, PetAction.DIZZY)

    def test_finite_action_returns_to_idle(self) -> None:
        self.machine.request(PetAction.HAPPY, now=2.0, reason="pat")
        self.machine.update(now=2.11)
        self.assertEqual(self.machine.current, PetAction.IDLE)


class AnimationPlayerTests(unittest.TestCase):
    @staticmethod
    def clip(action: PetAction, source_name: str) -> AnimationClip:
        frame = ClipFrame(Path(source_name), object())  # type: ignore[arg-type]
        return AnimationClip(
            action=action,
            asset_id=source_name,
            frames=(frame,),
            loop=True,
            duration_ms=None,
            frame_duration_ms=100,
            anchor=Anchor(),
            effect="breath",
            quality="source",
            requires_real_frames=False,
        )

    def test_crossfade_keeps_previous_layer_only_for_same_art(self) -> None:
        player = AnimationPlayer()
        player.play(self.clip(PetAction.IDLE, "shared.png"), crossfade=False)
        player.tick(0.1)
        player.play(self.clip(PetAction.HAPPY, "shared.png"))
        during = player.snapshot()
        self.assertEqual(during.current.action, PetAction.HAPPY)
        self.assertIsNotNone(during.previous)
        player.tick(0.2)
        after = player.snapshot()
        self.assertIsNone(after.previous)

    def test_different_pose_does_not_leave_a_ghost_layer(self) -> None:
        player = AnimationPlayer()
        player.play(self.clip(PetAction.IDLE, "idle.png"), crossfade=False)
        player.tick(0.1)
        player.play(self.clip(PetAction.HAPPY, "happy.png"))
        self.assertIsNone(player.snapshot().previous)


class AssetManifestTests(unittest.TestCase):
    def test_manifest_declares_required_states_and_formal_walk_cycle(self) -> None:
        root = Path(__file__).resolve().parents[1]
        registry = AssetRegistry(root / "assets")
        self.assertTrue(set(PetAction).issubset(registry.specs))
        walking = registry.specs[PetAction.WALKING]
        self.assertFalse(walking.requires_real_frames)
        self.assertEqual(walking.quality, "formal_unified_generated_walk_frames")
        manifest = json.loads((root / "assets" / "manifests" / "actions.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["assets"]["walk_side"]["frame_count"], 4)
        self.assertEqual(len(manifest["assets"]["walk_side"]["frames"]["238"]), 4)


if __name__ == "__main__":
    unittest.main()
