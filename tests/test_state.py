import random
from dataclasses import replace

import pytest

from okey.cards import ALL_CARDS, mask_of, parse_card, parse_cards
from okey.combos import combos_in, make_combo
from okey.rules import OFFICIAL_2026
from okey.state import (
    Discard,
    Draw,
    GameState,
    IllegalActionError,
    Phase,
    Play,
    apply,
    legal_actions,
)

RULES = OFFICIAL_2026
STRICT = replace(OFFICIAL_2026, name="strict", discard_requires_no_combo=True)


def draw_all(state: GameState, text: str) -> GameState:
    for card in parse_cards(text):
        state = apply(state, Draw(card), RULES)
    return state


def play(state: GameState, text: str, rules=RULES) -> GameState:
    return apply(state, Play(make_combo(parse_cards(text))), rules)


def assert_card_conservation(state: GameState) -> None:
    total = (
        state.hand.bit_count()
        + 3 * len(state.played)
        + state.discarded.bit_count()
        + state.deck_remaining
    )
    assert total == len(ALL_CARDS)


def test_new_game_waits_for_draw():
    state = GameState()
    assert state.phase(RULES) is Phase.AWAITING_DRAW
    assert state.deck_remaining == 24
    assert {a.card for a in legal_actions(state, RULES)} == set(ALL_CARDS)


def test_initial_deal_fills_hand():
    state = draw_all(GameState(), "K3 K4 K5 M4 S8")
    assert state.phase(RULES) is Phase.DECIDE
    assert state.deck_remaining == 19
    assert set(state.hand_cards) == set(parse_cards("K3 K4 K5 M4 S8"))


def test_cannot_draw_into_full_hand():
    state = draw_all(GameState(), "K3 K4 K5 M4 S8")
    with pytest.raises(IllegalActionError, match="masa dolu"):
        apply(state, Draw(parse_card("K1")), RULES)


def test_same_card_cannot_be_drawn_twice():
    state = draw_all(GameState(), "K3")
    with pytest.raises(IllegalActionError, match="zaten görüldü"):
        apply(state, Draw(parse_card("K3")), RULES)


def test_play_updates_score_hand_and_deck():
    state = draw_all(GameState(), "K3 K4 K5 M4 S8")
    after = play(state, "K3 K4 K5")
    assert after.score == 70
    assert set(after.hand_cards) == set(parse_cards("M4 S8"))
    assert [str(c) for c in after.played] == ["K3-K4-K5"]
    assert after.deck_remaining == 19
    assert after.phase(RULES) is Phase.AWAITING_DRAW
    assert_card_conservation(after)


def test_played_and_discarded_cards_cannot_return():
    state = draw_all(GameState(), "K3 K4 K5 M4 S8")
    state = play(state, "K3 K4 K5")
    state = draw_all(state, "K1 K2 M1")
    state = apply(state, Discard(parse_card("S8")), RULES)
    for code in ["K3", "K4", "K5", "S8"]:
        card = parse_card(code)
        assert not state.unseen & card.bit
        assert Draw(card) not in legal_actions(state, RULES)
        with pytest.raises(IllegalActionError, match="zaten görüldü"):
            apply(state, Draw(card), RULES)


def test_play_requires_cards_on_table():
    state = draw_all(GameState(), "K3 K4 M4 S4 S8")
    with pytest.raises(IllegalActionError, match="masada değil"):
        play(state, "K3 K4 K5")


def test_played_card_cannot_be_reused_in_second_combo():
    state = draw_all(GameState(), "K3 K4 K5 M4 S4")
    state = play(state, "K3 K4 K5")
    state = draw_all(state, "M5 M6 S5")
    with pytest.raises(IllegalActionError):
        play(state, "K4 M4 S4")


def test_no_play_or_discard_while_awaiting_draw():
    state = draw_all(GameState(), "K3 K4 K5 M4")
    with pytest.raises(IllegalActionError, match="Masa eksik"):
        play(state, "K3 K4 K5")
    with pytest.raises(IllegalActionError, match="Masa eksik"):
        apply(state, Discard(parse_card("M4")), RULES)


def test_discard_moves_card():
    state = draw_all(GameState(), "K1 M3 S5 K7 M8")
    after = apply(state, Discard(parse_card("K1")), RULES)
    assert after.discarded_cards == (parse_card("K1"),)
    assert after.score == 0
    assert after.hand.bit_count() == 4
    assert_card_conservation(after)
    with pytest.raises(IllegalActionError, match="masada değil"):
        apply(draw_all(after, "K2"), Discard(parse_card("K1")), RULES)


def test_discard_allowed_with_combo_by_default_but_not_in_strict_rules():
    state = draw_all(GameState(), "K3 K4 K5 M4 S8")
    assert Discard(parse_card("S8")) in legal_actions(state, RULES)
    apply(state, Discard(parse_card("S8")), RULES)

    assert all(isinstance(a, Play) for a in legal_actions(state, STRICT))
    with pytest.raises(IllegalActionError, match="yasak"):
        apply(state, Discard(parse_card("S8")), STRICT)


def test_strict_rules_allow_discard_without_combo():
    state = draw_all(GameState(), "K1 M3 S5 K7 M8")
    assert len(legal_actions(state, STRICT)) == 5
    apply(state, Discard(parse_card("K1")), STRICT)


def test_legal_actions_in_decide_phase():
    state = draw_all(GameState(), "K3 K4 K5 M4 S4")
    actions = legal_actions(state, RULES)
    plays = {str(a.combo) for a in actions if isinstance(a, Play)}
    discards = {a.card for a in actions if isinstance(a, Discard)}
    assert plays == {"K3-K4-K5", "K3-M4-K5", "K3-S4-K5", "K4-M4-S4"}
    assert discards == set(state.hand_cards)


def _state_with_deck_empty(hand_text: str) -> GameState:
    hand = mask_of(parse_cards(hand_text))
    rest = mask_of(c for c in ALL_CARDS if not hand & c.bit)
    return GameState(hand=hand, discarded=rest)


def test_finished_when_deck_empty_and_no_combo():
    state = _state_with_deck_empty("K1 M3 S5")
    assert state.phase(RULES) is Phase.FINISHED
    assert legal_actions(state, RULES) == []
    with pytest.raises(IllegalActionError, match="Oyun bitti"):
        apply(state, Discard(parse_card("K1")), RULES)


def test_game_continues_with_empty_deck_while_combo_exists():
    state = _state_with_deck_empty("K6 K7 K8 M1")
    assert state.phase(RULES) is Phase.DECIDE
    after = play(state, "K6 K7 K8")
    assert after.score == 100
    assert after.phase(RULES) is Phase.FINISHED


def test_apply_does_not_mutate_input():
    state = draw_all(GameState(), "K3 K4 K5 M4 S8")
    snapshot = (state.hand, state.played, state.discarded, state.score)
    play(state, "K3 K4 K5")
    apply(state, Discard(parse_card("S8")), RULES)
    assert (state.hand, state.played, state.discarded, state.score) == snapshot


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hand": mask_of(parse_cards("K1")), "discarded": mask_of(parse_cards("K1"))},
        {"hand": mask_of(parse_cards("K3")), "played": (make_combo(parse_cards("K3 K4 K5")),)},
        {"played": (make_combo(parse_cards("K3 K4 K5")), make_combo(parse_cards("K5 M5 S5")))},
        {"hand": 1 << 24},
        {"score": -10},
    ],
)
def test_inconsistent_state_rejected(kwargs):
    with pytest.raises(ValueError):
        GameState(**kwargs)


@pytest.mark.parametrize("seed", range(200))
@pytest.mark.parametrize("rules", [RULES, STRICT], ids=["default", "strict"])
def test_random_full_games_keep_invariants(seed, rules):
    rng = random.Random(seed)
    deck = list(ALL_CARDS)
    rng.shuffle(deck)
    state = GameState()
    for _ in range(100):  # 24 çekme + en fazla 24 oynama/atma
        phase = state.phase(rules)
        if phase is Phase.FINISHED:
            break
        if phase is Phase.AWAITING_DRAW:
            action = Draw(deck.pop())
        else:
            action = rng.choice(legal_actions(state, rules))
        state = apply(state, action, rules)
        assert_card_conservation(state)
        assert state.hand.bit_count() <= rules.hand_size
    else:
        pytest.fail("Oyun sınırlı adımda bitmedi")

    assert not deck
    assert state.deck_remaining == 0
    assert combos_in(state.hand) == []
    assert state.score == sum(c.points(rules) for c in state.played)
    assert rules.chest_for(state.score) is not None
