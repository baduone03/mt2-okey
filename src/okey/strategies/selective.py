"""Seçici açgözlü politika.

Açgözlü politika, masada bulduğu her üçlüyü (10-20 puanlık karışık seriler dahil) hemen
oynar ve kartları harcar. Seçici politika, destede kart varken yalnızca puanı
`min_points` ve üstü olan üçlüleri oynar; aksi halde en az işe yarayan kartı atar.
Kartın değeri de yalnızca bu eşiği geçen üçlüler üzerinden hesaplanır.

Eşik (varsayılan 50) ayrı bir deste kümesinde (tohum 777, 5.000 oyun) seçilmiştir;
doğrulaması farklı destelerdedir (docs/BENCHMARKS.md).
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from okey import fast
from okey.cards import Card
from okey.rules import RuleConfig
from okey.state import Action, Discard, GameState, IllegalActionError, Phase, Play, can_discard
from okey.strategies.greedy import best_play, least_useful_card

DEFAULT_MIN_POINTS = 50


class SelectivePolicy:
    def __init__(self, min_points: int = DEFAULT_MIN_POINTS) -> None:
        if min_points < 0:
            raise ValueError(f"Eşik negatif olamaz: {min_points}")
        self.min_points = min_points
        self.name = f"Seçici (≥{min_points})"

    def choose(self, state: GameState, rules: RuleConfig, rng: random.Random) -> Action:
        if state.phase(rules) is not Phase.DECIDE:
            raise IllegalActionError("Politika yalnızca karar aşamasında çağrılabilir.")
        combo = best_play(state, rules)
        if combo is not None and (
            combo.points(rules) >= self.min_points or not state.unseen or not can_discard(state, rules)
        ):
            return Play(combo)
        return Discard(least_useful_card(state, rules, self.min_points))

    def rollout_score(
        self, state: GameState, rules: RuleConfig, order: Sequence[Card], rng: random.Random
    ) -> int:
        """`play_out(state, ..., self, order).score` ile aynı sonucu hızlı motorla hesaplar."""
        return fast.rollout(
            state.hand,
            state.score,
            fast.order_bits(order),
            fast.tables(rules, self.min_points),
            self.min_points,
            rules.discard_requires_no_combo,
        )
