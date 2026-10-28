"""Strateji A: açgözlü politika.

- Masada geçerli üçlü varsa anlık puanı en yüksek olanı oynar.
- Yoksa geleceğe en az katkısı olan kartı atar: kartın hâlâ kurulabilir
  (diğer kartları masada veya görülmemiş) üçlülerinin toplam puanı en düşük olan.
Eşitlikler deterministik bozulur, böylece aynı durumda hep aynı hamle seçilir.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from okey import fast
from okey.cards import Card
from okey.combos import COMBOS_BY_CARD, Combo, combos_in
from okey.rules import RuleConfig
from okey.state import Action, Discard, GameState, IllegalActionError, Phase, Play, can_discard


def live_combos(state: GameState, card: Card) -> list[Combo]:
    """Kartı içeren ve diğer kartları hâlâ elde edilebilir (masada/görülmemiş) üçlüler."""
    available = state.hand | state.unseen
    return [c for c in COMBOS_BY_CARD[card.index] if c.mask & available == c.mask]


def discard_potential(state: GameState, card: Card, rules: RuleConfig, min_points: int = 0) -> int:
    """Kartın hâlâ kurulabilir ve puanı >= min_points olan üçlülerinin toplam puanı."""
    return sum(p for c in live_combos(state, card) if (p := c.points(rules)) >= min_points)


def best_play(state: GameState, rules: RuleConfig) -> Combo | None:
    combos = combos_in(state.hand)
    if not combos:
        return None
    # En yüksek puan; eşitlikte deterministik olarak maskesi küçük olan üçlü.
    return max(combos, key=lambda c: (c.points(rules), -c.mask))


def least_useful_card(state: GameState, rules: RuleConfig, min_points: int = 0) -> Card:
    return min(
        state.hand_cards,
        key=lambda card: (discard_potential(state, card, rules, min_points), card.number, card.color),
    )


class GreedyPolicy:
    name = "Açgözlü"

    def choose(self, state: GameState, rules: RuleConfig, rng: random.Random) -> Action:
        if state.phase(rules) is not Phase.DECIDE:
            raise IllegalActionError("Politika yalnızca karar aşamasında çağrılabilir.")
        combo = best_play(state, rules)
        if combo is not None:
            return Play(combo)
        if not can_discard(state, rules):  # üçlü yokken atma her zaman serbesttir
            raise IllegalActionError("Ne oynanabilir üçlü ne de atılabilir kart var.")
        return Discard(least_useful_card(state, rules))

    def rollout_score(
        self, state: GameState, rules: RuleConfig, order: Sequence[Card], rng: random.Random
    ) -> int:
        """`play_out(state, ..., self, order).score` ile aynı sonucu hızlı motorla hesaplar."""
        return fast.rollout(state.hand, state.score, fast.order_bits(order), fast.tables(rules))
