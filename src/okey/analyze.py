"""Oynanmış bir oyunun kaydını analiz eder.

Kullanım:
    python -m okey.analyze "+K3 +K4 +K5 +M4 +S8 O:K3-K4-K5 +K1 ..."

Rapor:
- oyun sonu puanı ve sandık;
- aynı kart sırasıyla kusursuz (sırayı bilen) oyunun azami puanı, yani 300'ün o destede
  mümkün olup olmadığı;
- her karar anında yapılan hamle, sistemin önerisi ve ikisinin tahmini 300+ olasılığı.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from okey.advisor import recommend
from okey.cards import Card
from okey.rules import OFFICIAL_2026, RuleConfig
from okey.session import GameSession, describe_action, from_log
from okey.state import Draw, GameState
from okey.strategies.greedy import GreedyPolicy
from okey.strategies.pimc import oracle_max_score


@dataclass(frozen=True)
class DecisionReview:
    step: int  # karar sırası (1'den)
    state: GameState
    played: str
    recommended: str
    played_p_silver: float  # yapılan hamlenin tahmini P(>= gümüş eşiği)
    best_p_silver: float  # önerilen hamlenin tahmini P(>= gümüş eşiği)
    exact: bool  # kesin oyun sonu hesabı mı

    @property
    def matches(self) -> bool:
        return self.played == self.recommended


@dataclass(frozen=True)
class GameReview:
    final_score: int
    chest: str
    draws: tuple[Card, ...]
    oracle_score: int | None  # tüm deste çekildiyse kusursuz oyunun azami puanı
    decisions: tuple[DecisionReview, ...]


def review(session: GameSession, n_simulations: int = 500) -> GameReview:
    rules = session.rules
    draws = tuple(e.card for e in session.events if isinstance(e, Draw))
    oracle = oracle_max_score(draws, rules) if len(draws) == 24 else None
    decisions = []
    for i, action in enumerate(session.events):
        if isinstance(action, Draw):
            continue
        state = session.states[i]
        advice = recommend(state, rules, n_simulations, rollout=GreedyPolicy(use_max=True))
        played_est = advice.evaluation.estimate_for(action)
        decisions.append(
            DecisionReview(
                step=len(decisions) + 1,
                state=state,
                played=describe_action(action, rules),
                recommended=describe_action(advice.best.action, rules),
                played_p_silver=played_est.p_silver_or_better,
                best_p_silver=advice.best.estimate.p_silver_or_better,
                exact=bool(getattr(played_est, "exact", False)),
            )
        )
    final = session.state.score
    return GameReview(final, rules.chest_for(final).value, draws, oracle, tuple(decisions))


def format_review(r: GameReview, rules: RuleConfig = OFFICIAL_2026) -> str:
    lines = [f"Oyun sonu: {r.final_score} puan ({r.chest} sandık)"]
    if r.oracle_score is not None:
        possible = "mümkündü" if r.oracle_score >= rules.chest_thresholds.silver else "mümkün değildi"
        lines.append(
            f"Kusursuz oyun (kart sırasını bilerek) bu destede en fazla {r.oracle_score} puan "
            f"alabilirdi; 300 {possible}."
        )
    else:
        lines.append("Destenin tamamı kayıtta yok; kusursuz oyun tavanı hesaplanamadı.")
    lines.append("")
    for d in r.decisions:
        mark = "✓" if d.matches else "≠"
        kind = "kesin" if d.exact else "tahmin"
        lines.append(
            f"{d.step:2}. {mark} puan {d.state.score:3} | masa {' '.join(c.code for c in d.state.hand_cards)}"
        )
        lines.append(f"     yapılan:  {d.played}  (300+ şansı %{100 * d.played_p_silver:.0f}, {kind})")
        if not d.matches:
            lines.append(f"     önerilen: {d.recommended}  (300+ şansı %{100 * d.best_p_silver:.0f})")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Oynanmış bir Okey oyununun kaydını analiz eder.")
    parser.add_argument("log", help='Oyun kaydı, örn. "+K3 +K4 +K5 +M4 +S8 O:K3-K4-K5 ..."')
    parser.add_argument("--n", type=int, default=500, help="Karar başına simülasyon")
    args = parser.parse_args(argv)
    print(format_review(review(from_log(args.log), args.n)))


if __name__ == "__main__":
    main()
