from dataclasses import replace

from okey.board import Zone, card_zone, handle_card_click, selected_action
from okey.cards import parse_card, parse_cards
from okey.rules import OFFICIAL_2026
from okey.session import GameSession
from okey.state import Discard, Phase, Play, legal_actions

NONE = frozenset()


def click_all(session: GameSession, text: str) -> GameSession:
    for card in parse_cards(text):
        result = handle_card_click(session, NONE, card)
        assert result.message is None, result.message
        session = result.session
    return session


def test_clicks_enter_cards_and_second_click_removes():
    session = click_all(GameSession(), "K1 K2")
    assert card_zone(session.state, parse_card("K1")) is Zone.HAND
    result = handle_card_click(session, NONE, parse_card("K1"))
    assert result.message is None
    assert card_zone(result.session.state, parse_card("K1")) is Zone.UNSEEN
    assert result.session.state.hand_cards == (parse_card("K2"),)


def test_full_hand_click_toggles_selection():
    session = click_all(GameSession(), "K3 K4 K5 M4 S8")
    assert session.phase is Phase.DECIDE
    r = handle_card_click(session, NONE, parse_card("K3"))
    assert r.selection == {parse_card("K3")}
    assert r.session is session
    r = handle_card_click(session, r.selection, parse_card("K3"))
    assert r.selection == NONE


def test_unseen_click_rejected_when_hand_full():
    session = click_all(GameSession(), "K3 K4 K5 M4 S8")
    r = handle_card_click(session, NONE, parse_card("K1"))
    assert r.session is session
    assert "Masa dolu" in r.message


def test_played_and_discarded_cards_cannot_be_entered_again():
    session = click_all(GameSession(), "K3 K4 K5 M4 S8")
    session = click_all(session.play(parse_cards("K3 K4 K5")), "K1 K2 M1").discard(parse_card("S8"))
    for code, zone in [("K3", Zone.PLAYED), ("S8", Zone.DISCARDED)]:
        card = parse_card(code)
        assert card_zone(session.state, card) is zone
        r = handle_card_click(session, NONE, card)
        assert r.session is session
        assert "Geri al" in r.message


def test_correction_blocked_after_decision():
    session = click_all(GameSession(), "K3 K4 K5 M4 S8").discard(parse_card("S8"))
    r = handle_card_click(session, NONE, parse_card("M4"))
    assert r.session is session
    assert "geri alın" in r.message


def test_finished_game_ignores_clicks():
    session = GameSession()
    while session.phase is not Phase.FINISHED:
        if session.phase is Phase.AWAITING_DRAW:
            session = session.draw(session.state.unseen_cards[0])
        else:
            session = session.act(legal_actions(session.state, session.rules)[0])
    r = handle_card_click(session, frozenset({parse_card("K1")}), parse_card("K1"))
    assert r.session is session
    assert r.selection == NONE
    assert "Oyun bitti" in r.message


def test_selected_action():
    session = click_all(GameSession(), "K3 K4 K5 M4 S8")
    action, _ = selected_action(session, frozenset(parse_cards("K5 K3 K4")))
    assert action == Play(session.play(parse_cards("K3 K4 K5")).state.played[0])
    action, _ = selected_action(session, frozenset({parse_card("S8")}))
    assert action == Discard(parse_card("S8"))
    action, msg = selected_action(session, frozenset(parse_cards("K3 K4 S8")))
    assert action is None and "geçerli bir üçlü değil" in msg
    action, msg = selected_action(session, frozenset(parse_cards("K3 K4")))
    assert action is None and "2 kart" in msg
    assert selected_action(session, NONE)[0] is None


def test_selected_discard_respects_strict_rule():
    strict = replace(OFFICIAL_2026, name="strict", discard_requires_no_combo=True)
    session = click_all(GameSession(strict), "K3 K4 K5 M4 S8")
    action, msg = selected_action(session, frozenset({parse_card("S8")}))
    assert action is None and "yasak" in msg


# --- Sade ekran ---

from okey.board import cards_needed, handle_simple_click  # noqa: E402


def simple_click_all(session: GameSession, text: str) -> GameSession:
    for card in parse_cards(text):
        result = handle_simple_click(session, card)
        assert result.message is None, result.message
        session = result.session
    return session


def test_simple_click_enters_and_removes_cards():
    session = simple_click_all(GameSession(), "K1 K2 K3 M4 S8")
    assert session.phase is Phase.DECIDE
    assert cards_needed(session) == 0
    fixed = handle_simple_click(session, parse_card("S8"))  # masa doluyken bile düzeltme
    assert fixed.message is None
    assert cards_needed(fixed.session) == 1
    assert parse_card("S8") not in fixed.session.state.hand_cards


def test_simple_click_rejects_unseen_when_full_and_used_cards():
    session = simple_click_all(GameSession(), "K3 K4 K5 M4 S8")
    r = handle_simple_click(session, parse_card("K1"))
    assert r.session is session and "Yaptım" in r.message
    after = session.play(parse_cards("K3 K4 K5"))
    assert cards_needed(after) == 3
    r = handle_simple_click(after, parse_card("K3"))
    assert r.session is after and "Geri al" in r.message


def test_simple_click_cannot_remove_card_before_a_move():
    session = simple_click_all(GameSession(), "K1 M3 S5 K7 M8").discard(parse_card("K1"))
    session = simple_click_all(session, "S8")
    r = handle_simple_click(session, parse_card("M3"))  # M3 hamleden önce girilmişti
    assert r.session is session and "geri alın" in r.message
    assert handle_simple_click(session, parse_card("S8")).message is None  # yeni giriş silinebilir


def test_cards_needed_near_end_of_deck():
    from okey.cards import ALL_CARDS, mask_of
    from okey.state import GameState

    hand = mask_of(parse_cards("K1 M3"))
    unseen = mask_of(parse_cards("S5"))
    state = GameState(hand=hand, discarded=mask_of(ALL_CARDS) & ~hand & ~unseen)
    session = GameSession(OFFICIAL_2026, (), (state,))
    assert cards_needed(session) == 1
