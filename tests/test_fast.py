"""Hızlı rollout motorunun referans yol (state.apply + GreedyPolicy) ile birebir eşitliği."""

import random
from dataclasses import replace

import pytest

from okey import fast
from okey.cards import ALL_CARDS, FULL_MASK
from okey.rules import OFFICIAL_2026, RuleConfig
from okey.simulation import deck_order, play_out
from okey.state import Draw, GameState, Phase, apply
from okey.strategies import GreedyPolicy, RandomPolicy
from okey.strategies.base import rollout_score
from okey.strategies.greedy import best_play, least_useful_card

RULES = OFFICIAL_2026
ODD = RuleConfig(
    name="tuhaf",
    same_number_points=(90, 10, 80, 20, 70, 30, 60, 40),
    same_color_run_points=(5, 5, 5, 5, 5, 5),
    mixed_run_points=(60, 50, 40, 30, 20, 10),
    hand_size=6,
)


def random_states(n: int, rules: RuleConfig, seed: int):
    """Rastgele politikayla oynanmış oyunlardan karar anları."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        deck = list(ALL_CARDS)
        rng.shuffle(deck)
        state = GameState()
        while state.phase(rules) is not Phase.FINISHED:
            if state.phase(rules) is Phase.AWAITING_DRAW:
                state = apply(state, Draw(deck.pop()), rules)
                continue
            if rng.random() < 0.3:
                out.append(state)
            state = apply(state, RandomPolicy().choose(state, rules, rng), rules)
    return out[:n]


@pytest.mark.parametrize("rules", [RULES, ODD], ids=["official", "odd"])
def test_tables_match_greedy_decisions(rules):
    t = fast.tables(rules)
    for state in random_states(300, rules, seed=1):
        combo = best_play(state, rules)
        got = fast.best_combo(state.hand, t)
        assert (got is None) == (combo is None)
        if combo is not None:
            assert got == (combo.mask, combo.points(rules))
        else:
            assert fast.least_useful(state.hand, state.hand | state.unseen, t) == least_useful_card(state, rules).bit


@pytest.mark.parametrize("rules", [RULES, ODD], ids=["official", "odd"])
def test_fast_rollout_equals_reference(rules):
    greedy = GreedyPolicy()
    for k, state in enumerate(random_states(400, rules, seed=2)):
        order = deck_order(state.unseen, 99, k)
        reference = play_out(state, rules, greedy, order, random.Random(0)).score
        assert greedy.rollout_score(state, rules, order, random.Random(0)) == reference


def test_full_games_equal_reference():
    greedy = GreedyPolicy()
    for i in range(500):
        order = deck_order(FULL_MASK, 5, i)
        assert rollout_score(greedy, GameState(), RULES, order, random.Random(0)) == (
            play_out(GameState(), RULES, greedy, order, random.Random(0)).score
        )


def test_rollout_score_falls_back_for_policies_without_fast_path():
    order = deck_order(FULL_MASK, 3, 0)
    rp = RandomPolicy()
    assert rollout_score(rp, GameState(), RULES, order, random.Random(4)) == (
        play_out(GameState(), RULES, rp, order, random.Random(4)).score
    )


def test_tables_cached_per_rules():
    assert fast.tables(RULES) is fast.tables(replace(RULES))
    assert fast.tables(RULES) is not fast.tables(ODD)


# --- Seçici politika ---

from okey.strategies import SelectivePolicy  # noqa: E402

STRICT = replace(OFFICIAL_2026, name="strict", discard_requires_no_combo=True)


@pytest.mark.parametrize("rules", [RULES, ODD, STRICT], ids=["official", "odd", "strict"])
@pytest.mark.parametrize("min_points", [0, 30, 50, 70])
def test_selective_fast_rollout_equals_reference(rules, min_points):
    policy = SelectivePolicy(min_points)
    for k, state in enumerate(random_states(150, rules, seed=3 + min_points)):
        order = deck_order(state.unseen, 55, k)
        reference = play_out(state, rules, policy, order, random.Random(0)).score
        assert policy.rollout_score(state, rules, order, random.Random(0)) == reference


def test_selective_zero_threshold_is_greedy():
    sel, greedy = SelectivePolicy(0), GreedyPolicy()
    for k, state in enumerate(random_states(200, RULES, seed=9)):
        assert sel.choose(state, RULES, random.Random(0)) == greedy.choose(state, RULES, random.Random(0))
        order = deck_order(state.unseen, 66, k)
        assert sel.rollout_score(state, RULES, order, None) == greedy.rollout_score(state, RULES, order, None)


# --- En değerli üçlüye göre atma ---


@pytest.mark.parametrize("rules", [RULES, ODD, STRICT], ids=["official", "odd", "strict"])
@pytest.mark.parametrize("min_points", [0, 50])
def test_max_value_fast_rollout_equals_reference(rules, min_points):
    policy = SelectivePolicy(min_points, use_max=True) if min_points else GreedyPolicy(use_max=True)
    for k, state in enumerate(random_states(150, rules, seed=21 + min_points)):
        order = deck_order(state.unseen, 71, k)
        reference = play_out(state, rules, policy, order, random.Random(0)).score
        assert policy.rollout_score(state, rules, order, random.Random(0)) == reference


def test_max_value_keeps_high_card():
    from okey.cards import mask_of, parse_card, parse_cards
    from okey.state import Discard
    from okey.strategies.greedy import discard_potential

    state = GameState(hand=mask_of(parse_cards("K8 K7 M3 S4 M1")))
    # Toplam değerde 8 (yalnızca 6-7-8 ve 8-8-8) düşük kalır; en değerli üçlüsü ise 100.
    assert discard_potential(state, parse_card("K8"), RULES, use_max=True) == 100
    action = GreedyPolicy(use_max=True).choose(state, RULES, random.Random(0))
    assert action != Discard(parse_card("K8"))
    assert GreedyPolicy(use_max=True).name != GreedyPolicy().name
    assert GreedyPolicy.name == "Açgözlü"
