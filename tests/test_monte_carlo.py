import random
from itertools import permutations

import pytest

from okey.cards import ALL_CARDS, FULL_MASK, mask_of, parse_card, parse_cards
from okey.combos import make_combo
from okey.rules import OFFICIAL_2026
from okey.simulation import play_after, policy_rng
from okey.state import Discard, Draw, GameState, IllegalActionError, Phase, Play, apply, legal_actions
from okey.strategies import GreedyPolicy
from okey.strategies.monte_carlo import CandidateEstimate, MonteCarloPolicy, evaluate, rank

RULES = OFFICIAL_2026


def endgame(hand: str, unseen: str, score: int) -> GameState:
    """Masada `hand`, destede `unseen` kalan; diğer kartlar atılmış sayılır."""
    hand_mask = mask_of(parse_cards(hand))
    rest = FULL_MASK & ~hand_mask & ~mask_of(parse_cards(unseen))
    return GameState(hand=hand_mask, discarded=rest, score=score)


# Rastgele oyunlarda bulunmuş gerçek bir oyun sonu: açgözlü K4-M5-S6 (+40) oynar ve
# her deste sırasında 290'da (bronz) kalır; M5'i atmak her sırada >= 300 getirir.
SILVER_TRAP = dict(hand="K2 K4 M5 S2 S6", unseen="K3 K8 S1 S7", score=240)


def test_requires_decision_phase_and_positive_n():
    with pytest.raises(IllegalActionError):
        evaluate(GameState(), RULES)
    state = endgame(**SILVER_TRAP)
    with pytest.raises(ValueError):
        evaluate(state, RULES, n_simulations=0)


def test_exact_mode_matches_brute_force():
    state = endgame(**SILVER_TRAP)
    ev = evaluate(state, RULES, n_simulations=100, seed=3)
    assert ev.exact
    assert ev.n_simulations == 24  # 4! sıra
    assert ev.rollout_policy == "Açgözlü"
    orders = list(permutations(state.unseen_cards))
    for cand in ev.candidates:
        expected = sorted(
            play_after(state, cand.action, RULES, GreedyPolicy(), o, random.Random(0)).score
            for o in orders
        )
        assert sorted(cand.scores) == expected


def test_monte_carlo_avoids_greedy_silver_trap():
    state = endgame(**SILVER_TRAP)
    greedy_action = GreedyPolicy().choose(state, RULES, random.Random(0))
    assert greedy_action == Play(make_combo(parse_cards("K4 M5 S6")))
    ev = evaluate(state, RULES, n_simulations=100)
    assert ev.best.action == Discard(parse_card("M5"))
    assert ev.best.p_silver_or_better == 1.0
    assert min(ev.best.scores) >= 300
    greedy = ev.estimate_for(greedy_action)
    assert set(greedy.scores) == {290}
    assert greedy.p_silver_or_better == 0.0


def _exact_endgames(limit: int):
    """Açgözlü oynanan rastgele oyunlardan, destede <= 4 kart kalan karar anları."""
    found = 0
    for seed in range(10_000):
        rng = random.Random(seed)
        deck = list(ALL_CARDS)
        rng.shuffle(deck)
        state = GameState()
        while state.phase(RULES) is not Phase.FINISHED:
            if state.phase(RULES) is Phase.AWAITING_DRAW:
                state = apply(state, Draw(deck.pop()), RULES)
                continue
            if state.deck_remaining <= 4:
                yield state
                found += 1
                break
            state = apply(state, GreedyPolicy().choose(state, RULES, rng), RULES)
        if found >= limit:
            return


def test_choice_never_worse_than_greedy_in_exact_mode():
    """Rollout özelliği: kesin modda seçim, açgözlü seçimden sözlüksel olarak kötü olamaz."""
    for state in _exact_endgames(60):
        ev = evaluate(state, RULES, n_simulations=100)
        assert ev.exact
        greedy = ev.estimate_for(GreedyPolicy().choose(state, RULES, random.Random(0)))
        assert ev.best.sort_key() >= greedy.sort_key()
        assert ev.best.sort_key() == max(c.sort_key() for c in ev.candidates)


def test_common_random_numbers_and_reproducibility():
    state = GameState(hand=mask_of(parse_cards("K3 K4 K5 M4 S8")))
    play = Play(make_combo(parse_cards("K3 K4 K5")))
    full = evaluate(state, RULES, n_simulations=60, seed=11)
    alone = evaluate(state, RULES, n_simulations=60, seed=11, actions=[play])
    assert not full.exact
    assert full.n_simulations == 60
    # Bir adayın tahmini, başka adayların varlığından bağımsızdır (aynı deste sıraları).
    assert full.estimate_for(play).scores == alone.estimate_for(play).scores
    assert evaluate(state, RULES, n_simulations=60, seed=11) == full
    assert evaluate(state, RULES, n_simulations=60, seed=12).estimate_for(play).scores != alone.estimate_for(play).scores
    assert {c.action for c in full.candidates} == set(legal_actions(state, RULES))


def test_estimate_properties_are_consistent():
    state = GameState(hand=mask_of(parse_cards("K6 K7 K8 M7 S7")), score=150)
    ev = evaluate(state, RULES, n_simulations=80, seed=5)
    for c in ev.candidates:
        assert c.n == 80
        bronze = sum(s < 300 for s in c.scores) / c.n
        assert c.p_gold + c.p_silver + bronze == pytest.approx(1.0)
        assert c.gold_ci[0] <= c.p_gold <= c.gold_ci[1]
        assert c.silver_ci[0] <= c.p_silver <= c.silver_ci[1]
        assert min(c.scores) <= c.median_score <= max(c.scores)
        assert c.score_se >= 0
        assert all(s >= 150 + c.immediate_points for s in c.scores)
    assert ev.tied_with_best[0] is True


def _cand(scores, label):
    return CandidateEstimate(Discard(parse_card(label)), 0, tuple(scores), 400, 300)


def test_rank_ignores_insignificant_gold_difference():
    a = _cand([400] * 10 + [200] * 90, "K1")  # altın %10, ortalama 220
    b = _cand([400] * 9 + [300] * 91, "K2")  # altın %9 (fark tek örnek), gümüş+ %100
    ordered, tied = rank([a, b])
    assert ordered[0] is b
    assert tied == [True, False]


def test_rank_respects_significant_gold_difference():
    a = _cand([400] * 50 + [0] * 50, "K1")  # altın %50
    b = _cand([390] * 100, "K2")  # altın %0, ortalama daha yüksek
    ordered, _ = rank([a, b])
    assert ordered[0] is a


def test_rank_with_zero_tolerance_is_lexicographic():
    a = _cand([400] * 10 + [200] * 90, "K1")
    b = _cand([400] * 9 + [300] * 91, "K2")
    ordered, _ = rank([a, b], z=0.0)
    assert ordered[0] is a


def test_monte_carlo_policy_plays_legal_full_game():
    policy = MonteCarloPolicy(n_simulations=8)
    rng = random.Random(1)
    deck = list(ALL_CARDS)
    rng.shuffle(deck)
    state = GameState()
    while state.phase(RULES) is not Phase.FINISHED:
        if state.phase(RULES) is Phase.AWAITING_DRAW:
            state = apply(state, Draw(deck.pop()), RULES)
        else:
            action = policy.choose(state, RULES, rng)
            assert action in legal_actions(state, RULES)
            state = apply(state, action, RULES)
    assert state.score == sum(c.points(RULES) for c in state.played)
