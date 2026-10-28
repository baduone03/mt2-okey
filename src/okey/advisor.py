"""Hamle önerileri (arayüzden bağımsız).

- `greedy_recommendation`: Strateji A (açgözlü), simülasyonsuz ve anında.
- `recommend`: Strateji B (Monte Carlo); her aday hamle için sandık olasılıkları,
  beklenen puan ve belirsizlik içerir. Sonuçlar kesin olasılık değil, tahmindir.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from okey.cards import Card
from okey.combos import ComboKind, combos_in
from okey.rules import RuleConfig
from okey.state import Action, Discard, GameState, Phase, Play
from okey.strategies.greedy import GreedyPolicy, discard_potential, live_combos
from okey.strategies.monte_carlo import CandidateEstimate, Evaluation, evaluate

GREEDY_STRATEGY = "Açgözlü (Strateji A)"
MC_STRATEGY = "Monte Carlo (Strateji B)"
GREEDY_LIMITATION = "Açgözlü strateji yalnızca anlık puana bakar; gelecekte gelecek kartları hesaba katmaz."


@dataclass(frozen=True)
class Recommendation:
    action: Action
    strategy: str
    immediate_points: int
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    estimate: CandidateEstimate | None = None
    is_greedy_choice: bool = False
    tied_with_best: bool = False

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


@dataclass(frozen=True)
class Advice:
    recommendations: tuple[Recommendation, ...]  # en iyi öneri ilk sırada
    evaluation: Evaluation

    @property
    def best(self) -> Recommendation:
        return self.recommendations[0]


def explain(state: GameState, action: Action, rules: RuleConfig) -> tuple[list[str], list[str]]:
    """Bir eylemin olasılıktan bağımsız avantaj ve dezavantajları."""
    if isinstance(action, Play):
        return _explain_play(state, action, rules)
    return _explain_discard(state, action, rules)


def _explain_play(state: GameState, action: Play, rules: RuleConfig) -> tuple[list[str], list[str]]:
    combo = action.combo
    points = combo.points(rules)
    pros = [f"Anında +{points} puan ({combo.kind.value})."]
    if state.score < rules.chest_thresholds.gold <= state.score + points:
        pros.append("Bu hamleyle altın sandık eşiğine ulaşılır.")
    others = [c for c in combos_in(state.hand) if c != combo]
    if others and all(points >= c.points(rules) for c in others):
        pros.append(f"Masadaki {len(others) + 1} geçerli üçlünün en yüksek puanlısı.")

    cons = []
    clashing = [c for c in others if c.mask & combo.mask]
    if clashing:
        listed = ", ".join(f"{c} (+{c.points(rules)})" for c in clashing[:3])
        more = f" ve {len(clashing) - 3} diğer" if len(clashing) > 3 else ""
        cons.append(f"Aynı kartları kullanan seçenekler kaybolur: {listed}{more}.")
    if combo.kind is ComboKind.MIXED_RUN:
        bonus = rules.same_color_run_points[combo.low - 1] - points
        cons.append(f"Karışık seri: aynı numaralar tek renkten olsaydı +{bonus} daha fazla puan verirdi.")
    return pros, cons


def _explain_discard(state: GameState, action: Discard, rules: RuleConfig) -> tuple[list[str], list[str]]:
    card = action.card
    live = live_combos(state, card)
    potential = discard_potential(state, card, rules)
    on_table = combos_in(state.hand)
    pros, cons = [], []
    if on_table:
        pros.append("Masadaki kartları ileride daha değerli üçlüler kurmak için saklar.")
        cons.append(f"Masada {len(on_table)} geçerli üçlü varken bu tur puan alınmaz.")
    else:
        pros.append("Masada geçerli üçlü yok; bir kart atmak gerekiyor.")
    if live:
        cons.append(
            f"{card} ile kurulabilecek {len(live)} olası üçlü kalıcı olarak kaybolur "
            f"(toplam {potential} puan potansiyeli)."
        )
    else:
        pros.append(f"{card} ile kurulabilecek hiçbir üçlü kalmadı; atmanın kaybı yok.")
    return pros, cons


def greedy_recommendation(state: GameState, rules: RuleConfig) -> Recommendation | None:
    if state.phase(rules) is not Phase.DECIDE:
        return None
    action = GreedyPolicy().choose(state, rules, random.Random(0))  # deterministik politika
    pros, cons = explain(state, action, rules)
    if isinstance(action, Discard) and not combos_in(state.hand):
        pros.append(f"{action.card} masadaki kartlar arasında geleceğe en az katkısı olan kart.")
    cons.append(GREEDY_LIMITATION)
    points = action.combo.points(rules) if isinstance(action, Play) else 0
    return Recommendation(action, GREEDY_STRATEGY, points, tuple(pros), tuple(cons), is_greedy_choice=True)


def decision_seed(state: GameState) -> int:
    """Aynı karar anında aynı tahmini üretmek için durumdan türetilen tohum."""
    return ((state.hand * 31 + state.discarded) * 31 + state.played_mask) & 0xFFFF_FFFF_FFFF


def _percent(p: float) -> str:
    return f"%{100 * p:.1f}"


def recommend(
    state: GameState, rules: RuleConfig, n_simulations: int = 500, seed: int | None = None
) -> Advice | None:
    """Tüm aday hamleleri Monte Carlo ile değerlendirir; karar aşaması dışında None."""
    if state.phase(rules) is not Phase.DECIDE:
        return None
    seed = decision_seed(state) if seed is None else seed
    ev = evaluate(state, rules, n_simulations, seed)
    greedy_action = GreedyPolicy().choose(state, rules, random.Random(0))
    greedy_est = ev.estimate_for(greedy_action)
    best = ev.best

    recs = []
    for cand, tied in zip(ev.candidates, ev.tied_with_best):
        pros, cons = explain(state, cand.action, rules)
        is_greedy = cand.action == greedy_action
        if cand is best and not is_greedy:
            parts = []
            if cand.p_gold > greedy_est.p_gold:
                parts.append(f"altın olasılığı {_percent(greedy_est.p_gold)} → {_percent(cand.p_gold)}")
            if cand.p_silver_or_better > greedy_est.p_silver_or_better:
                parts.append(
                    "gümüş-veya-üstü olasılığı "
                    f"{_percent(greedy_est.p_silver_or_better)} → {_percent(cand.p_silver_or_better)}"
                )
            if cand.mean_score > greedy_est.mean_score:
                parts.append(f"beklenen puan {greedy_est.mean_score:.0f} → {cand.mean_score:.0f}")
            if parts:
                pros.append(
                    f"Açgözlü seçime ({greedy_action_title(greedy_action, rules)}) göre: {', '.join(parts)}."
                )
        if tied and cand is not best:
            cons.append("En iyi öneriden istatistiksel olarak ayırt edilemiyor; daha fazla simülasyonla netleşebilir.")
        recs.append(
            Recommendation(
                action=cand.action,
                strategy=MC_STRATEGY,
                immediate_points=cand.immediate_points,
                pros=tuple(pros),
                cons=tuple(cons),
                estimate=cand,
                is_greedy_choice=is_greedy,
                tied_with_best=tied,
            )
        )
    return Advice(tuple(recs), ev)


def greedy_action_title(action: Action, rules: RuleConfig) -> str:
    if isinstance(action, Play):
        return f"{action.combo}, +{action.combo.points(rules)}"
    return f"{action.card} atmak"
