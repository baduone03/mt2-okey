"""Kurallara uygun eylemlerden birini düzgün dağılımla seçen temel politika."""

from __future__ import annotations

import random

from okey.rules import RuleConfig
from okey.state import Action, GameState, IllegalActionError, Phase, legal_actions


class RandomPolicy:
    name = "Rastgele"

    def choose(self, state: GameState, rules: RuleConfig, rng: random.Random) -> Action:
        if state.phase(rules) is not Phase.DECIDE:
            raise IllegalActionError("Politika yalnızca karar aşamasında çağrılabilir.")
        return rng.choice(legal_actions(state, rules))
