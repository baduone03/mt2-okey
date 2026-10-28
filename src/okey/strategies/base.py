"""Politika arayüzü."""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Protocol

from okey.cards import Card

from okey.rules import RuleConfig
from okey.state import Action, GameState


class Policy(Protocol):
    """Karar aşamasındaki (Phase.DECIDE) bir durumda oynanacak eylemi seçer."""

    name: str

    def choose(self, state: GameState, rules: RuleConfig, rng: random.Random) -> Action: ...


def rollout_score(
    policy: Policy, state: GameState, rules: RuleConfig, order: Sequence[Card], rng: random.Random
) -> int:
    """Oyunu politika ile sonuna kadar oynar; politikanın hızlı yolu varsa onu kullanır."""
    fast_path = getattr(policy, "rollout_score", None)
    if fast_path is not None:
        return fast_path(state, rules, order, rng)
    from okey.simulation import play_out  # döngüsel içe aktarmayı önler

    return play_out(state, rules, policy, order, rng).score
