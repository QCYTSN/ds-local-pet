"""Data-driven, lightweight animation primitives for the desktop pet."""

from .clip import PetAction
from .state_machine import ActionStateMachine

__all__ = ["ActionStateMachine", "PetAction"]
