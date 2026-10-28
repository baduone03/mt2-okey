"""Strateji B: Monte Carlo rollout (bir adım politika iyileştirme).

Her aday eylem için aynı deste sıraları (ortak rastgele sayılar) kullanılarak eylem
uygulanır ve oyun bir devam politikasıyla (varsayılan: açgözlü) sonuna kadar oynanır.
Kalan kart sayısı küçükse ve tüm sıralar örneklem bütçesine sığıyorsa her sıra tek tek
denenir; bu durumda sonuç devam politikasına göre kesindir (`exact=True`).

Seçim kuralı (gürültüye dayanıklı sözlüksel sıralama):
1. Altın olasılığı en yüksek adaya göre istatistiksel olarak anlamlı biçimde kötü
   olmayan adaylar tutulur (eşleştirilmiş fark <= z * standart hata).
2. Bunlar arasında gümüş-veya-üstü olasılığı için aynı eleme yapılır.
3. Kalanlar arasında beklenen puanı en yüksek olan seçilir.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from itertools import permutations

from okey.cards import Card, cards_of
from okey.rules import RuleConfig
from okey.simulation import deck_orders, play_after, policy_rng
from okey.state import Action, GameState, IllegalActionError, Phase, Play, legal_actions
from okey.stats import Z_95, mean_and_se, median, paired_difference, wilson_interval
from okey.strategies.base import Policy
from okey.strategies.greedy import GreedyPolicy


@dataclass(frozen=True)
class CandidateEstimate:
    action: Action
    immediate_points: int
    scores: tuple[int, ...]  # oyun sonu puanları; i'inci değer i'inci deste sırasına ait
    gold_threshold: int
    silver_threshold: int

    @property
    def n(self) -> int:
        return len(self.scores)

    @cached_property
    def gold_flags(self) -> tuple[int, ...]:
        return tuple(int(s >= self.gold_threshold) for s in self.scores)

    @cached_property
    def silver_plus_flags(self) -> tuple[int, ...]:
        return tuple(int(s >= self.silver_threshold) for s in self.scores)

    @property
    def gold_hits(self) -> int:
        return sum(self.gold_flags)

    @property
    def silver_hits(self) -> int:
        """Tam gümüş kademesi (gümüş eşiği <= puan < altın eşiği)."""
        return sum(self.silver_plus_flags) - self.gold_hits

    @property
    def p_gold(self) -> float:
        return self.gold_hits / self.n

    @property
    def p_silver(self) -> float:
        return self.silver_hits / self.n

    @property
    def p_silver_or_better(self) -> float:
        return sum(self.silver_plus_flags) / self.n

    @property
    def gold_ci(self) -> tuple[float, float]:
        return wilson_interval(self.gold_hits, self.n)

    @property
    def silver_ci(self) -> tuple[float, float]:
        return wilson_interval(self.silver_hits, self.n)

    @cached_property
    def mean_score(self) -> float:
        return mean_and_se(self.scores)[0]

    @cached_property
    def score_se(self) -> float:
        return mean_and_se(self.scores)[1]

    @property
    def median_score(self) -> float:
        return median(self.scores)

    def sort_key(self) -> tuple[float, float, float]:
        return (self.p_gold, self.p_silver_or_better, self.mean_score)


@dataclass(frozen=True)
class Evaluation:
    candidates: tuple[CandidateEstimate, ...]  # en iyi aday ilk sırada
    tied_with_best: tuple[bool, ...]  # en iyiden istatistiksel olarak ayırt edilemeyenler
    n_simulations: int
    exact: bool
    rollout_policy: str
    seed: int

    @property
    def best(self) -> CandidateEstimate:
        return self.candidates[0]

    def estimate_for(self, action: Action) -> CandidateEstimate:
        for candidate in self.candidates:
            if candidate.action == action:
                return candidate
        raise KeyError(f"Aday bulunamadı: {action}")


def _immediate_points(action: Action, rules: RuleConfig) -> int:
    return action.combo.points(rules) if isinstance(action, Play) else 0


def _not_worse(best: Sequence[int], other: Sequence[int], z: float) -> bool:
    diff, se = paired_difference(best, other)
    return diff <= z * se


def _orders(state: GameState, n: int, seed: int) -> tuple[list[tuple[Card, ...]], bool]:
    remaining = state.deck_remaining
    if math.factorial(remaining) <= n:
        return [tuple(p) for p in permutations(cards_of(state.unseen))], True
    return deck_orders(state.unseen, n, seed), False


def rank(candidates: Sequence[CandidateEstimate], z: float = Z_95) -> tuple[list[CandidateEstimate], list[bool]]:
    """Adayları seçim kuralına göre sıralar; en iyi aday ilk sıradadır."""
    if not candidates:
        raise ValueError("Değerlendirilecek aday yok")
    pool = list(candidates)
    top_gold = max(pool, key=lambda c: (c.p_gold, c.p_silver_or_better, c.mean_score))
    pool = [c for c in pool if _not_worse(top_gold.gold_flags, c.gold_flags, z)]
    top_silver = max(pool, key=lambda c: (c.p_silver_or_better, c.p_gold, c.mean_score))
    pool = [c for c in pool if _not_worse(top_silver.silver_plus_flags, c.silver_plus_flags, z)]
    best = max(pool, key=lambda c: (c.mean_score, c.p_gold, c.p_silver_or_better))

    rest = sorted((c for c in candidates if c is not best), key=CandidateEstimate.sort_key, reverse=True)
    ordered = [best, *rest]
    tied = [
        c is best
        or (
            _not_worse(best.gold_flags, c.gold_flags, z)
            and _not_worse(best.silver_plus_flags, c.silver_plus_flags, z)
            and _not_worse(best.scores, c.scores, z)
        )
        for c in ordered
    ]
    return ordered, tied


def evaluate(
    state: GameState,
    rules: RuleConfig,
    n_simulations: int = 500,
    seed: int = 0,
    rollout: Policy | None = None,
    actions: Sequence[Action] | None = None,
) -> Evaluation:
    """Karar aşamasındaki her aday eylemi aynı deste sıralarıyla değerlendirir."""
    if n_simulations < 1:
        raise ValueError(f"Simülasyon sayısı en az 1 olmalı: {n_simulations}")
    if state.phase(rules) is not Phase.DECIDE:
        raise IllegalActionError("Değerlendirme yalnızca karar aşamasında yapılabilir.")
    rollout = rollout or GreedyPolicy()
    actions = list(actions) if actions is not None else legal_actions(state, rules)
    orders, exact = _orders(state, n_simulations, seed)

    estimates = []
    for action in actions:
        scores = tuple(
            play_after(state, action, rules, rollout, order, policy_rng(seed, i)).score
            for i, order in enumerate(orders)
        )
        estimates.append(
            CandidateEstimate(
                action=action,
                immediate_points=_immediate_points(action, rules),
                scores=scores,
                gold_threshold=rules.chest_thresholds.gold,
                silver_threshold=rules.chest_thresholds.silver,
            )
        )
    # Kesin modda tahmin gürültüsü yoktur; eleme saf sözlüksel karşılaştırmaya iner.
    ordered, tied = rank(estimates, z=0.0 if exact else Z_95)
    return Evaluation(tuple(ordered), tuple(tied), len(orders), exact, rollout.name, seed)


class MonteCarloPolicy:
    """Her kararda `evaluate` ile en iyi adayı seçen politika (benchmark için)."""

    def __init__(self, n_simulations: int = 200, rollout: Policy | None = None) -> None:
        self.n_simulations = n_simulations
        self.rollout = rollout or GreedyPolicy()
        self.name = f"Monte Carlo (N={n_simulations}, devam: {self.rollout.name})"

    def choose(self, state: GameState, rules: RuleConfig, rng: random.Random) -> Action:
        seed = rng.getrandbits(48)
        return evaluate(state, rules, self.n_simulations, seed, self.rollout).best.action
