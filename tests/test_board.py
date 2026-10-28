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
