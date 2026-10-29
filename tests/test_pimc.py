import random
from dataclasses import replace

import pytest

from okey import fast
from okey.cards import ALL_CARDS, FULL_MASK, mask_of, parse_card, parse_cards
from okey.rules import OFFICIAL_2026
from okey.simulation import deck_order
from okey.state import Discard, Draw, GameState, IllegalActionError, Phase, apply, legal_actions
from okey.strategies import GreedyPolicy, RandomPolicy
from okey.strategies.pimc import PIMC_NAME, OracleSolver, PimcPolicy, evaluate_pimc, oracle_max_score

RULES = OFFICIAL_2026
STRICT = replace(OFFICIAL_2026, name="strict", discard_requires_no_combo=True)


def endgame(hand: str, unseen: str, score: int = 0) -> GameState:
    hand_mask = mask_of(parse_cards(hand))
    rest = FULL_MASK & ~hand_mask & ~mask_of(parse_cards(unseen))
    return GameState(hand=hand_mask, discarded=rest, score=score)


def brute_force_max(state: GameState, order, rules) -> int:
    """Bilinen sırayla tüm hamle dizilerini deneyerek azami oyun sonu puanı (referans)."""
    best = 0
    stack = [(state, 0)]
    while stack:
        st, k = stack.pop()
        phase = st.phase(rules)
        if phase is Phase.FINISHED:
            best = max(best, st.score)
        elif phase is Phase.AWAITING_DRAW:
            stack.append((apply(st, Draw(order[k]), rules), k + 1))
        else:
            for action in legal_actions(st, rules):
                stack.append((apply(st, action, rules), k))
    return best


def random_endgames(n: int, rules, seed: int, max_unseen: int = 4):
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
                out.append(st)
                break
            st = apply(st, RandomPolicy().choose(st, rules, rng), rules)
    return out


@pytest.mark.parametrize("rules", [RULES, STRICT], ids=["default", "strict"])
def test_oracle_matches_brute_force(rules):
    solver = OracleSolver(rules)
    for k, st in enumerate(random_endgames(40, rules, seed=5)):
        order = deck_order(st.unseen, 3, k)
        value = solver.best_after([st.hand], fast.order_bits(order))[0]
        assert st.score + value == brute_force_max(st, order, rules)


def test_oracle_max_score_full_game_bounds():
    for i in range(5):
        order = deck_order(FULL_MASK, 2026, i)
        top = oracle_max_score(order, RULES)
        greedy = GreedyPolicy().rollout_score(GameState(), RULES, order, None)
        assert top >= greedy
        assert top % 10 == 0 and 0 < top <= 600


def test_evaluate_requires_decision_phase_and_samples():
    with pytest.raises(IllegalActionError):
        evaluate_pimc(GameState(), RULES)
    with pytest.raises(ValueError):
        evaluate_pimc(endgame("K1 K2 K3 M5 S7", "S8"), RULES, n_samples=0)


def test_pimc_avoids_silver_trap():
    # Bkz. test_monte_carlo.SILVER_TRAP: açgözlü K4-M5-S6 oynar ve 290'da kalır.
    st = endgame("K2 K4 M5 S2 S6", "K3 K8 S1 S7", 240)
    ev = evaluate_pimc(st, RULES, n_samples=24, seed=1)
    assert ev.rollout_policy == PIMC_NAME
    assert ev.best.action == Discard(parse_card("M5"))
    assert min(ev.best.scores) >= 300


def test_pimc_keeps_eights_over_low_cards():
    # Masada 6-7-8 serisine aday iki kart ve önemsiz bir 1: kahin 8'i değil 1'i atmayı seçer.
    st = GameState(hand=mask_of(parse_cards("K7 K8 M1 S3 M5")))
    ev = evaluate_pimc(st, RULES, n_samples=12, seed=3)
    assert isinstance(ev.best.action, Discard)
    assert ev.best.action.card.number < 7


def test_evaluation_covers_actions_and_is_reproducible():
    st = GameState(hand=mask_of(parse_cards("K3 K4 K5 M4 S8")))
    ev = evaluate_pimc(st, RULES, n_samples=6, seed=9)
    assert {c.action for c in ev.candidates} == set(legal_actions(st, RULES))
    assert all(c.n == 6 for c in ev.candidates)
    assert ev.tied_with_best[0]
    assert evaluate_pimc(st, RULES, n_samples=6, seed=9) == ev
    keys = [(c.gold_hits, sum(c.silver_plus_flags), sum(c.scores)) for c in ev.candidates]
    assert keys == sorted(keys, reverse=True)


def test_pimc_respects_strict_rules():
    st = GameState(hand=mask_of(parse_cards("K1 M2 S3 K8 M6")))
    ev = evaluate_pimc(st, STRICT, n_samples=4, seed=0)
    assert all(not isinstance(c.action, Discard) for c in ev.candidates)


def test_pimc_policy_plays_legal_game():
    policy = PimcPolicy(n_samples=3)
    rng = random.Random(2)
    order = deck_order(FULL_MASK, 11, 0)
    st, k = GameState(), 0
    while st.phase(RULES) is not Phase.FINISHED:
        if st.phase(RULES) is Phase.AWAITING_DRAW:
            st = apply(st, Draw(order[k]), RULES)
            k += 1
        else:
            action = policy.choose(st, RULES, rng)
            assert action in legal_actions(st, RULES)
            st = apply(st, action, RULES)
    assert st.score == sum(c.points(RULES) for c in st.played)
