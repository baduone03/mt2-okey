"""Hamle önerileri (arayüzden bağımsız).

Şimdilik yalnızca Strateji A (açgözlü) önerisi üretilir. Olasılık tahminleri
(altın/gümüş sandık, beklenen puan) Monte Carlo aşamasında eklenecektir.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from okey.cards import Card
from okey.combos import ComboKind, combos_in
from okey.rules import RuleConfig
from okey.state import Action, Discard, GameState, Phase, Play
from okey.strategies.greedy import GreedyPolicy, discard_potential, live_combos


@dataclass(frozen=True)
class Recommendation:
    action: Action
    strategy: str
    immediate_points: int
    pros: tuple[str, ...]
    cons: tuple[str, ...]

    @property
    def cards(self) -> tuple[Card, ...]:
        if isinstance(self.action, Play):
            return self.action.combo.cards
        return (self.action.card,)

    @property
    def title(self) -> str:
        if isinstance(self.action, Play):
            return f"Oyna {self.action.combo} (+{self.immediate_points})"
        return f"At {self.action.card}"


GREEDY_LIMITATION = "Açgözlü strateji yalnızca anlık puana bakar; gelecekte gelecek kartları hesaba katmaz."


def greedy_recommendation(state: GameState, rules: RuleConfig) -> Recommendation | None:
    if state.phase(rules) is not Phase.DECIDE:
        return None
    action = GreedyPolicy().choose(state, rules, random.Random(0))  # deterministik politika
    if isinstance(action, Play):
        return _explain_play(state, action, rules)
    return _explain_discard(state, action, rules)


def _explain_play(state: GameState, action: Play, rules: RuleConfig) -> Recommendation:
    combo = action.combo
    points = combo.points(rules)
    pros = [f"Anında +{points} puan ({combo.kind.value})."]
    if state.score < rules.chest_thresholds.gold <= state.score + points:
        pros.append("Bu hamleyle altın sandık eşiğine ulaşılır.")
    alternatives = [c for c in combos_in(state.hand) if c != combo]
    if alternatives:
        pros.append(f"Masadaki {len(alternatives) + 1} geçerli üçlünün en yüksek puanlısı.")

    cons = []
    clashing = [c for c in alternatives if c.mask & combo.mask]
    if clashing:
        listed = ", ".join(f"{c} (+{c.points(rules)})" for c in clashing[:3])
        more = f" ve {len(clashing) - 3} diğer" if len(clashing) > 3 else ""
        cons.append(f"Aynı kartları kullanan seçenekler kaybolur: {listed}{more}.")
    if combo.kind is ComboKind.MIXED_RUN:
        bonus = rules.same_color_run_points[combo.low - 1] - points
        cons.append(f"Karışık seri: aynı numaralar tek renkten olsaydı +{bonus} daha fazla puan verirdi.")
    cons.append(GREEDY_LIMITATION)
    return Recommendation(action, "Açgözlü (Strateji A)", points, tuple(pros), tuple(cons))


def _explain_discard(state: GameState, action: Discard, rules: RuleConfig) -> Recommendation:
    card = action.card
    live = live_combos(state, card)
    potential = discard_potential(state, card, rules)
    pros = ["Masada geçerli üçlü yok; bir kart atmak gerekiyor."]
    if live:
        pros.append(
            f"{card} masadaki kartlar arasında geleceğe en az katkısı olan kart "
            f"({len(live)} olası üçlü, toplam {potential} puan potansiyeli)."
        )
    else:
        pros.append(f"{card} ile kurulabilecek hiçbir üçlü kalmadı; atmanın kaybı yok.")
    cons = []
    if live:
        cons.append(f"{card} ile kurulabilecek {len(live)} olası üçlü kalıcı olarak kaybolur.")
    cons.append(GREEDY_LIMITATION)
    return Recommendation(action, "Açgözlü (Strateji A)", 0, tuple(pros), tuple(cons))
