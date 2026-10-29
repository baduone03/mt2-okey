"""Strateji C: PIMC (perfect-information Monte Carlo).

Her aday hamle için görülmemiş kartların N olası çekilme sırası örneklenir. Her sıra
için "kahin" çözücü, sırayı bildiği varsayımıyla oyunun sonuna kadar en yüksek puanı
veren planı bulur. Aday, örneklerin kaçında 400'e (sonra 300'e) ulaşılabildiğine ve
toplam puana göre seçilir.

Monte Carlo rollout'tan (bir adım + açgözlü devam) farkı: yüksek puanlı üçlüler için
kart saklamanın değerini görebilmesidir. Tahmini olasılıklar iyimserdir (kahin
gelecek kartları bilir); sıralama için kullanılır, kesin olasılık değildir.
İki bağımsız 300 oyunluk ölçümde Monte Carlo'ya göre altın farkı +4,7 ± 2,9 ve
−1,3 ± 3,2 puan çıktı; yani anlamlı bir üstünlüğü kanıtlanmadı (docs/BENCHMARKS.md).
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from okey import fast
from okey.cards import Card
from okey.rules import RuleConfig
from okey.simulation import deck_orders
from okey.state import Action, GameState, IllegalActionError, Phase, Play, legal_actions
from okey.strategies.monte_carlo import CandidateEstimate, Evaluation

PIMC_NAME = "Kahin planı (PIMC)"


class OracleSolver:
    """Bilinen bir çekilme sırası için oyun sonuna kadarki azami ek puanı hesaplar."""

    def __init__(self, rules: RuleConfig) -> None:
        self.rules = rules
        self.tables = fast.tables(rules)
        self._hand_combos: dict[int, tuple[tuple[int, int], ...]] = {}
        self._hand_bits: dict[int, tuple[int, ...]] = {}

    def hand_combos(self, hand: int) -> tuple[tuple[int, int], ...]:
        combos = self._hand_combos.get(hand)
        if combos is None:
            combos = tuple((m, p) for m, p in self.tables.combos if m & hand == m)
            self._hand_combos[hand] = combos
        return combos

    def hand_bits(self, hand: int) -> tuple[int, ...]:
        bits = self._hand_bits.get(hand)
        if bits is None:
            out, rest = [], hand
            while rest:
                bit = rest & -rest
                rest ^= bit
                out.append(bit)
            bits = self._hand_bits[hand] = tuple(out)
        return bits

    def best_after(self, hands_after: Sequence[int], order: Sequence[int]) -> list[int]:
        """Her başlangıç masası için (hamle uygulanmış, henüz doldurulmamış) azami ek puan.

        Tüm adaylar aynı sırayı paylaştığından ara sonuçlar ortak bellekte tutulur.
        """
        n = len(order)
        hand_size = self.tables.hand_size
        strict = self.rules.discard_requires_no_combo
        memo: dict[int, int] = {}
        hand_combos, hand_bits = self.hand_combos, self.hand_bits

        def refill(hand: int, i: int) -> tuple[int, int]:
            while i < n and hand.bit_count() < hand_size:
                hand |= order[i]
                i += 1
            return hand, i

        def best(i: int, hand: int) -> int:
            key = (i << 24) | hand
            value = memo.get(key)
            if value is not None:
                return value
            value = 0
            combos = hand_combos(hand)
            for mask, points in combos:
                h2, i2 = refill(hand & ~mask, i)
                total = points + best(i2, h2)
                if total > value:
                    value = total
            if i < n and not (strict and combos):
                for bit in hand_bits(hand):
                    h2, i2 = refill(hand & ~bit, i)
                    total = best(i2, h2)
                    if total > value:
                        value = total
            memo[key] = value
            return value

        results = []
        for start in hands_after:
            hand, i = refill(start, 0)
            results.append(best(i, hand))
        return results


def _after(state: GameState, action: Action, rules: RuleConfig) -> tuple[int, int]:
    """Hamleden sonraki masa (doldurulmamış) ve kazanılan puan."""
    if isinstance(action, Play):
        return state.hand & ~action.combo.mask, action.combo.points(rules)
    return state.hand & ~action.card.bit, 0


def evaluate_pimc(
    state: GameState,
    rules: RuleConfig,
    n_samples: int = 20,
    seed: int = 0,
    actions: Sequence[Action] | None = None,
) -> Evaluation:
    """Adayları kahin planlarıyla değerlendirir; en iyi aday ilk sırada.

    Sıralama: 400'e ulaşılan örnek sayısı, sonra 300'e ulaşılan, sonra toplam puan.
    `CandidateEstimate.scores`, her örnekte kahinin ulaşabildiği oyun sonu puanıdır.
    """
    if n_samples < 1:
        raise ValueError(f"Örnek sayısı en az 1 olmalı: {n_samples}")
    if state.phase(rules) is not Phase.DECIDE:
        raise IllegalActionError("Değerlendirme yalnızca karar aşamasında yapılabilir.")
    actions = list(actions) if actions is not None else legal_actions(state, rules)
    afters = [_after(state, a, rules) for a in actions]
    solver = OracleSolver(rules)
    scores: list[list[int]] = [[] for _ in actions]
    for order in deck_orders(state.unseen, n_samples, seed):
        values = solver.best_after([h for h, _ in afters], fast.order_bits(order))
        for j, ((_, points), value) in enumerate(zip(afters, values)):
            scores[j].append(state.score + points + value)

    gold, silver = rules.chest_thresholds.gold, rules.chest_thresholds.silver
    estimates = [
        CandidateEstimate(a, pts, tuple(s), gold, silver) for a, (_, pts), s in zip(actions, afters, scores)
    ]

    def key(c: CandidateEstimate) -> tuple[int, int, int]:
        return (c.gold_hits, sum(c.silver_plus_flags), sum(c.scores))

    ordered = sorted(estimates, key=key, reverse=True)
    best_key = key(ordered[0])
    tied = tuple(key(c) == best_key for c in ordered)
    return Evaluation(tuple(ordered), tied, n_samples, False, PIMC_NAME, seed)


class PimcPolicy:
    """Her kararda `evaluate_pimc` ile seçim yapan politika."""

    def __init__(self, n_samples: int = 20) -> None:
        self.n_samples = n_samples
        self.name = f"PIMC (N={n_samples})"

    def choose(self, state: GameState, rules: RuleConfig, rng: random.Random) -> Action:
        return evaluate_pimc(state, rules, self.n_samples, rng.getrandbits(48)).best.action


def oracle_max_score(order: Sequence[Card], rules: RuleConfig) -> int:
    """Baştan, sırası bilinen bir destede ulaşılabilecek azami puan (kahin tavanı)."""
    return OracleSolver(rules).best_after([0], fast.order_bits(order))[0]
