import random
from dataclasses import replace

import pytest

from okey.cards import ALL_CARDS, mask_of, parse_card, parse_cards
from okey.combos import make_combo
from okey.rules import OFFICIAL_2026
from okey.state import Discard, Draw, GameState, IllegalActionError, Phase, Play, apply, legal_actions
from okey.strategies import GreedyPolicy, RandomPolicy
from okey.strategies.greedy import discard_potential, live_combos

RULES = OFFICIAL_2026
STRICT = replace(OFFICIAL_2026, name="strict", discard_requires_no_combo=True)
RNG = random.Random(0)


def hand_state(text: str, gone: str = "") -> GameState:
    """Masada `text`, oynanmış sayılmadan desteden çıkmış (atılmış) `gone` kartları."""
    return GameState(hand=mask_of(parse_cards(text)), discarded=mask_of(parse_cards(gone)))


def test_greedy_plays_highest_scoring_combo():
    state = hand_state("K6 K7 K8 M7 S7")
    # K6-K7-K8 = 100, K7-M7-S7 = 80, K6-M7-K8 / K6-S7-K8 = 60
    assert GreedyPolicy().choose(state, RULES, RNG) == Play(make_combo(parse_cards("K6 K7 K8")))


def test_greedy_prefers_combo_over_discard_even_if_small():
    state = hand_state("K1 M2 S3 K8 M8")
    assert GreedyPolicy().choose(state, RULES, RNG) == Play(make_combo(parse_cards("K1 M2 S3")))


def test_greedy_tie_break_is_deterministic():
    state = hand_state("K3 M3 S3 M4 S5")  # 3-3-3 = 40, K3-M4-S5 / M3-M4-S5 / S3-M4-S5 = 30
    first = GreedyPolicy().choose(state, RULES, random.Random(1))
    assert first == Play(make_combo(parse_cards("K3 M3 S3")))
    assert all(GreedyPolicy().choose(state, RULES, random.Random(s)) == first for s in range(5))


def test_live_combos_ignore_combos_with_gone_cards():
    state = hand_state("K1 M3 S5 K7 M8", gone="M2 S2 K2")
    # K1 yalnızca 1-1-1 ve 1-2-3 serilerinde olabilir; tüm 2'ler gitti -> sadece 1-1-1 kalır.
    assert [str(c) for c in live_combos(state, parse_card("K1"))] == ["K1-M1-S1"]
    assert discard_potential(state, parse_card("K1"), RULES) == 20


def test_greedy_discards_least_useful_card():
    # 1'lerin hepsi ve 2'lerin hepsi görüldü: K3'ün yalnızca 3-4-5 serileri ve 3-3-3 kalır,
    # K8 ise 6-7-8 serileri ve 8-8-8 ile çok daha yüksek potansiyele sahiptir.
    state = hand_state("K3 M5 S7 K8 M1", gone="K1 S1 K2 M2 S2")
    assert parse_card("M1") in state.hand_cards
    choice = GreedyPolicy().choose(state, RULES, RNG)
    assert choice == Discard(parse_card("M1"))  # M1: tüm üçlüleri ölü, potansiyel 0


def test_greedy_discard_matches_minimum_potential():
    state = hand_state("K1 M3 S5 K7 M8")
    action = GreedyPolicy().choose(state, RULES, RNG)
    assert isinstance(action, Discard)
    potentials = {c: discard_potential(state, c, RULES) for c in state.hand_cards}
    assert potentials[action.card] == min(potentials.values())


@pytest.mark.parametrize("policy", [GreedyPolicy(), RandomPolicy()], ids=lambda p: p.name)
def test_policy_rejects_non_decision_phase(policy):
    with pytest.raises(IllegalActionError):
        policy.choose(GameState(), RULES, RNG)


@pytest.mark.parametrize("rules", [RULES, STRICT], ids=["default", "strict"])
@pytest.mark.parametrize("policy", [GreedyPolicy(), RandomPolicy()], ids=lambda p: p.name)
def test_policies_only_choose_legal_actions(policy, rules):
    rng = random.Random(42)
    for seed in range(30):
        deck = list(ALL_CARDS)
        random.Random(seed).shuffle(deck)
        state = GameState()
        while state.phase(rules) is not Phase.FINISHED:
            if state.phase(rules) is Phase.AWAITING_DRAW:
                action = Draw(deck.pop())
            else:
                action = policy.choose(state, rules, rng)
                assert action in legal_actions(state, rules)
            state = apply(state, action, rules)


def test_random_policy_is_reproducible_and_varies():
    state = hand_state("K3 K4 K5 M4 S4")
    picks = [RandomPolicy().choose(state, RULES, random.Random(s)) for s in range(40)]
    again = [RandomPolicy().choose(state, RULES, random.Random(s)) for s in range(40)]
    assert picks == again
    assert len(set(picks)) > 3


# --- Seçici politika ---

from okey.strategies import SelectivePolicy  # noqa: E402


def test_selective_discards_instead_of_low_combo():
    state = hand_state("K1 M2 S3 K8 M6")  # tek üçlü: K1-M2-S3 = 10 puan, destede kart var
    action = SelectivePolicy(50).choose(state, RULES, RNG)
    assert isinstance(action, Discard)
    assert GreedyPolicy().choose(state, RULES, RNG) == Play(make_combo(parse_cards("K1 M2 S3")))


def test_selective_plays_combo_above_threshold():
    state = hand_state("K6 K7 K8 M1 S3")
    assert SelectivePolicy(50).choose(state, RULES, RNG) == Play(make_combo(parse_cards("K6 K7 K8")))


def test_selective_plays_low_combo_when_deck_empty_or_strict():
    full = mask_of(ALL_CARDS)
    hand = mask_of(parse_cards("K1 M2 S3 K8 M6"))
    empty_deck = GameState(hand=hand, discarded=full & ~hand)
    assert SelectivePolicy(50).choose(empty_deck, RULES, RNG) == Play(make_combo(parse_cards("K1 M2 S3")))
    state = hand_state("K1 M2 S3 K8 M6")
    assert SelectivePolicy(50).choose(state, STRICT, RNG) == Play(make_combo(parse_cards("K1 M2 S3")))


def test_selective_discard_ignores_low_value_potential():
    # K1'in canlı üçlüleri yalnızca düşük puanlı (1-1-1 = 20, 1-2-3 serileri <= 50);
    # eşik 60 iken potansiyeli 0 sayılır ve ilk atılan olur.
    state = hand_state("K1 M5 S7 K8 M3")
    assert SelectivePolicy(60).choose(state, RULES, RNG) == Discard(parse_card("K1"))


def test_selective_rejects_negative_threshold():
    with pytest.raises(ValueError):
        SelectivePolicy(-1)


@pytest.mark.parametrize("rules", [RULES, STRICT], ids=["default", "strict"])
def test_selective_only_chooses_legal_actions(rules):
    policy = SelectivePolicy()
    rng = random.Random(3)
    for seed in range(30):
        deck = list(ALL_CARDS)
        random.Random(seed).shuffle(deck)
        state = GameState()
        while state.phase(rules) is not Phase.FINISHED:
            if state.phase(rules) is Phase.AWAITING_DRAW:
                action = Draw(deck.pop())
            else:
                action = policy.choose(state, rules, rng)
                assert action in legal_actions(state, rules)
            state = apply(state, action, rules)
