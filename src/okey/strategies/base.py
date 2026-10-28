"""Politika arayüzü."""

from __future__ import annotations

import random
from typing import Protocol

from okey.rules import RuleConfig
from okey.state import Action, GameState


class Policy(Protocol):
    """Karar aşamasındaki (Phase.DECIDE) bir durumda oynanacak eylemi seçer."""

    name: str

    def choose(self, state: GameState, rules: RuleConfig, rng: random.Random) -> Action: ...
