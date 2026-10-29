import random
from dataclasses import replace
from functools import lru_cache

import pytest

from okey.cards import ALL_CARDS, FULL_MASK, mask_of, parse_card, parse_cards
from okey.rules import OFFICIAL_2026
from okey.state import Discard, Draw, GameState, IllegalActionError, Phase, apply, legal_actions
from okey.strategies import RandomPolicy
from okey.strategies.endgame import ENDGAME_NAME, EndgameSolver, evaluate_endgame

RULES = OFFICIAL_2026
STRICT = replace(OFFICIAL_2026, name="strict", discard_requires_no_combo=True)


def endgame(hand: str, unseen: str, score: int = 0) -> GameState:
    hand_mask = mask_of(parse_cards(hand))
    rest = FULL_MASK & ~hand_mask & ~mask_of(parse_cards(unseen))
    return GameState(hand=hand_mask, discarded=rest, score=score)


def reference_value(state: GameState, rules) -> tuple:
    """Kural motoruyla (GameState/apply) bağımsız expectimax; yavaş ama doğrudan."""

    @lru_cache(maxsize=None)
    def v(st: GameState):
        phase = st.phase(rules)
        if phase is Phase.FINISHED:
            s = st.score
            return (float(s >= 300), float(s >= 400), float(s))
        if phase is Phase.AWAITING_DRAW:
            vals = [v(apply(st, Draw(c), rules)) for c in st.unseen_cards]
            return tuple(sum(x[i] for x in vals) / len(vals) for i in range(3))
        return max(v(apply(st, a, rules)) for a in legal_actions(st, rules))

    return v(state)


def random_endgames(n, rules, seed, max_unseen=3):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        deck = list(ALL_CARDS)
        rng.shuffle(deck)
        st = GameState()
        while st.phase(rules) is not Phase.FINISHED:
            if st.phase(rules) is Phase.AWAITING_DRAW:
                st = apply(st, Draw(deck.pop()), rules)
                continue
            if st.deck_remaining <= max_unseen:
                st = replace(st, score=rng.choice([200, 250, 270, 280, 300, 350, 380]))
                out.append(st)
                break
            st = apply(st, RandomPolicy().choose(st, rules, rng), rules)
    return out


@pytest.mark.parametrize("rules", [RULES, STRICT], ids=["default", "strict"])
def test_values_match_reference_expectimax(rules):
    solver = EndgameSolver(rules)
    for st in random_endgames(25, rules, seed=3):
        for action in legal_actions(st, rules):
            after = apply(st, action, rules)
            expected = reference_value(after, rules)
            got = solver.value(after.hand, after.unseen, after.score)
            assert got == pytest.approx(expected)


@pytest.mark.parametrize("rules", [RULES, STRICT], ids=["default", "strict"])
def test_best_action_is_optimal(rules):
    for st in random_endgames(25, rules, seed=4):
        ev = evaluate_endgame(st, rules)
        best_ref = max(reference_value(apply(st, a, rules), rules) for a in legal_actions(st, rules))
        chosen = reference_value(apply(st, ev.best.action, rules), rules)
        assert chosen == pytest.approx(best_ref)


def test_distribution_is_consistent():
    for st in random_endgames(20, RULES, seed=5):
        ev = evaluate_endgame(st, RULES)
        for est in ev.candidates:
            assert sum(p for _, p in est.distribution) == pytest.approx(1.0)
            assert est.p_silver_or_better == pytest.approx(est.p_silver + est.p_gold)
            assert est.gold_ci == (est.p_gold, est.p_gold)
            assert est.score_se == 0.0 and est.exact
            assert min(s for s, _ in est.distribution) <= est.median_score <= max(s for s, _ in est.distribution)
        assert ev.exact and ev.rollout_policy == ENDGAME_NAME
        assert ev.tied_with_best[0]


def test_secures_silver_in_trap():
    # Açgözlü K4-M5-S6 oynar ve her sırada 290'da kalır; kesin hesap M5'i atıp 300'ü garantiler.
    st = endgame("K2 K4 M5 S2 S6", "K3 K8 S1 S7", 240)
    ev = evaluate_endgame(st, RULES)
    assert ev.best.action == Discard(parse_card("M5"))
    assert ev.best.p_silver_or_better == pytest.approx(1.0)


def test_requires_decision_phase():
    with pytest.raises(IllegalActionError):
        evaluate_endgame(GameState(), RULES)


def test_eight_card_endgame_is_fast_enough():
    import time

    rng = random.Random(8)
    deck = list(ALL_CARDS)
    rng.shuffle(deck)
    st = GameState()
    while st.deck_remaining > 8 or st.phase(RULES) is not Phase.DECIDE:
        if st.phase(RULES) is Phase.AWAITING_DRAW:
            st = apply(st, Draw(deck.pop()), RULES)
        else:
            st = apply(st, RandomPolicy().choose(st, RULES, rng), RULES)
    start = time.perf_counter()
    evaluate_endgame(st, RULES)
    assert time.perf_counter() - start < 30
