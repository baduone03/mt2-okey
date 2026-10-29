"""Kesin oyun sonu hesabı (expectimax).

Destede az kart kaldığında, kalan kartların gelebileceği her sıra ve her karar anındaki
en iyi hamle tam olarak hesaplanır. Amaç sözlükseldir: önce P(puan >= gümüş eşiği),
sonra P(puan >= altın eşiği), sonra beklenen puan. Kart çekişi görülmemiş kartlardan
düzgün rastgeledir.

Ölçüm (docs/BENCHMARKS.md, bölüm 8): destede <= 8 kart kalınca bu hesaba geçmek, 2.000
oyunda bronz oranını 0,9 ± 0,6 puan düşürdü ve ortalama puanı 5,2 ± 0,6 artırdı.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from okey import fast
from okey.rules import RuleConfig
from okey.state import Action, GameState, IllegalActionError, Phase, Play, legal_actions
from okey.strategies.monte_carlo import Evaluation

ENDGAME_CARDS = 8  # destede bu kadar veya daha az kart kalınca kesin hesap
ENDGAME_NAME = "Kesin oyun sonu hesabı"

Value = tuple[float, float, float]  # (P >= gümüş, P >= altın, E[puan])


@dataclass(frozen=True)
class ExactEstimate:
    """Bir hamlenin, sonrasında en iyi oyunla elde edilen kesin puan dağılımı.

    Arayüz için `CandidateEstimate` ile aynı alanları sunar; aralıklar sıfır genişliktedir.
    """

    action: Action
    immediate_points: int
    distribution: tuple[tuple[int, float], ...]  # (oyun sonu puanı, olasılık), puana göre sıralı
    gold_threshold: int
    silver_threshold: int
    exact: bool = True
    n: int = 0  # örneklem yok; arayüz "kesin" gösterir

    def _p(self, at_least: int) -> float:
        return sum(p for s, p in self.distribution if s >= at_least)

    @property
    def p_gold(self) -> float:
        return self._p(self.gold_threshold)

    @property
    def p_silver_or_better(self) -> float:
        return self._p(self.silver_threshold)

    @property
    def p_silver(self) -> float:
        return self.p_silver_or_better - self.p_gold

    @property
    def gold_ci(self) -> tuple[float, float]:
        return (self.p_gold, self.p_gold)

    @property
    def silver_ci(self) -> tuple[float, float]:
        return (self.p_silver, self.p_silver)

    @property
    def mean_score(self) -> float:
        return sum(s * p for s, p in self.distribution)

    @property
    def score_se(self) -> float:
        return 0.0

    @property
    def median_score(self) -> float:
        cumulative = 0.0
        for score, p in self.distribution:
            cumulative += p
            if cumulative >= 0.5 - 1e-12:
                return float(score)
        return float(self.distribution[-1][0])

    def sort_key(self) -> Value:
        return (self.p_silver_or_better, self.p_gold, self.mean_score)


class EndgameSolver:
    def __init__(self, rules: RuleConfig) -> None:
        self.rules = rules
        self.tables = fast.tables(rules)
        self.silver = rules.chest_thresholds.silver
        self.gold = rules.chest_thresholds.gold
        self._value: dict[tuple, Value] = {}
        self._dist: dict[tuple, dict[int, float]] = {}

    @staticmethod
    def _bits(mask: int) -> list[int]:
        out, rest = [], mask
        while rest:
            bit = rest & -rest
            rest ^= bit
            out.append(bit)
        return out

    def _options(self, hand: int, unseen: int) -> list[tuple[int, int]]:
        """Karar anındaki hamleler: (yeni masa, kazanılan puan)."""
        combos = [(hand & ~m, p) for m, p in self.tables.combos if m & hand == m]
        if unseen and not (self.rules.discard_requires_no_combo and combos):
            return combos + [(hand & ~bit, 0) for bit in self._bits(hand)]
        return combos

    def _best_option(self, hand: int, unseen: int, score: int) -> tuple[int, int] | None:
        best, best_value = None, None
        for new_hand, points in self._options(hand, unseen):
            value = self.value(new_hand, unseen, score + points)
            if best_value is None or value > best_value:
                best, best_value = (new_hand, points), value
        return best

    def value(self, hand: int, unseen: int, score: int) -> Value:
        """Masa doldurulmadan önceki durumun değeri (önce çekiş, sonra karar)."""
        key = (hand, unseen, score)
        cached = self._value.get(key)
        if cached is not None:
            return cached
        if hand.bit_count() < self.tables.hand_size and unseen:
            bits = self._bits(unseen)
            a = b = c = 0.0
            for bit in bits:
                x, y, z = self.value(hand | bit, unseen & ~bit, score)
                a, b, c = a + x, b + y, c + z
            result = (a / len(bits), b / len(bits), c / len(bits))
        else:
            option = self._best_option(hand, unseen, score)
            if option is None:
                result = (float(score >= self.silver), float(score >= self.gold), float(score))
            else:
                result = self.value(option[0], unseen, score + option[1])
        self._value[key] = result
        return result

    def distribution(self, hand: int, unseen: int, score: int) -> dict[int, float]:
        """En iyi oyunla oyun sonu puanının kesin dağılımı."""
        key = (hand, unseen, score)
        cached = self._dist.get(key)
        if cached is not None:
            return cached
        result: dict[int, float] = {}
        if hand.bit_count() < self.tables.hand_size and unseen:
            bits = self._bits(unseen)
            for bit in bits:
                for s, p in self.distribution(hand | bit, unseen & ~bit, score).items():
                    result[s] = result.get(s, 0.0) + p / len(bits)
        else:
            option = self._best_option(hand, unseen, score)
            if option is None:
                result = {score: 1.0}
            else:
                result = self.distribution(option[0], unseen, score + option[1])
        self._dist[key] = result
        return result


def _after(state: GameState, action: Action, rules: RuleConfig) -> tuple[int, int]:
    if isinstance(action, Play):
        return state.hand & ~action.combo.mask, action.combo.points(rules)
    return state.hand & ~action.card.bit, 0


def evaluate_endgame(
    state: GameState, rules: RuleConfig, actions: Sequence[Action] | None = None
) -> Evaluation:
    """Adayları kesin hesapla değerlendirir; en iyi aday ilk sırada."""
    if state.phase(rules) is not Phase.DECIDE:
        raise IllegalActionError("Değerlendirme yalnızca karar aşamasında yapılabilir.")
    actions = list(actions) if actions is not None else legal_actions(state, rules)
    solver = EndgameSolver(rules)
    estimates = []
    for action in actions:
        hand, points = _after(state, action, rules)
        dist = solver.distribution(hand, state.unseen, state.score + points)
        estimates.append(
            ExactEstimate(
                action=action,
                immediate_points=points,
                distribution=tuple(sorted(dist.items())),
                gold_threshold=rules.chest_thresholds.gold,
                silver_threshold=rules.chest_thresholds.silver,
            )
        )
    # Sıralama solver'ın tam değerleriyle (yuvarlama farkı olmasın diye) yapılır.
    keyed = [
        (solver.value(*_hand_unseen_score(state, a, rules)), i, e)
        for i, (a, e) in enumerate(zip(actions, estimates))
    ]
    keyed.sort(key=lambda t: (t[0], -t[1]), reverse=True)
    ordered = tuple(e for _, _, e in keyed)
    best_value = keyed[0][0]
    tied = tuple(v == best_value for v, _, _ in keyed)
    return Evaluation(ordered, tied, 0, True, ENDGAME_NAME, 0)  # type: ignore[arg-type]


def _hand_unseen_score(state: GameState, action: Action, rules: RuleConfig) -> tuple[int, int, int]:
    hand, points = _after(state, action, rules)
    return hand, state.unseen, state.score + points
