import random
from dataclasses import replace

import pytest

from okey.cards import ALL_CARDS, parse_card, parse_cards
from okey.rules import OFFICIAL_2026
from okey.session import GameSession, NothingToUndoError, describe_action
from okey.state import Discard, Draw, GameState, IllegalActionError, Phase, apply, legal_actions

RULES = OFFICIAL_2026
STRICT = replace(OFFICIAL_2026, name="strict", discard_requires_no_combo=True)


def draw_all(session: GameSession, text: str) -> GameSession:
    for card in parse_cards(text):
        session = session.draw(card)
    return session


def test_new_session():
    session = GameSession()
    assert session.state == GameState()
    assert session.phase is Phase.AWAITING_DRAW
    assert not session.can_undo
    assert session.history == []
    with pytest.raises(NothingToUndoError):
        session.undo()


def test_actions_update_state_and_history():
    session = draw_all(GameSession(), "K3 K4 K5 M4 S8")
    session = session.play(parse_cards("K5 K3 K4"))
    assert session.state.score == 70
    assert session.state.deck_remaining == 19
    assert len(session.history) == 6
    last = session.history[-1]
    assert last.index == 6
    assert last.state_after == session.state
    assert describe_action(last.action, RULES) == "Oynandı: K3-K4-K5 (aynı renk seri, +70)"
    assert describe_action(session.history[0].action, RULES) == "Çekildi: K3"


def test_undo_restores_previous_state_exactly():
    s1 = draw_all(GameSession(), "K3 K4 K5 M4 S8")
    s2 = s1.play(parse_cards("K3 K4 K5"))
    s3 = s2.draw(parse_card("K1"))
    assert s3.undo() == s2
    assert s3.undo().state == s2.state
    assert s3.undo().undo() == s1
    assert s3.undo().undo().state == s1.state
    assert s1.state.score == 0
    assert s1.state.deck_remaining == 19


def test_undone_card_can_be_entered_again():
    session = draw_all(GameSession(), "K3 K4 K5 M4 S8")
    session = session.discard(parse_card("S8"))
    with pytest.raises(IllegalActionError):
        session.draw(parse_card("S8"))
    restored = session.undo()
    assert restored.state.hand & parse_card("S8").bit
    # Yanlış girilen kart geri alınınca aynı kart tekrar girilebilir.
    wrong = restored.discard(parse_card("M4")).draw(parse_card("K1"))
    fixed = wrong.undo().undo()
    assert fixed.state == restored.state


def test_illegal_action_leaves_session_unchanged():
    session = draw_all(GameSession(), "K3 K4 K5 M4 S8")
    before = (session.events, session.state)
    with pytest.raises(IllegalActionError):
        session.draw(parse_card("K1"))
    with pytest.raises(IllegalActionError):
        session.play(parse_cards("K1 K2 K3"))
    assert (session.events, session.state) == before


def test_invalid_event_log_rejected():
    with pytest.raises(IllegalActionError):
        GameSession(RULES, (Draw(parse_card("K1")), Draw(parse_card("K1"))))


def test_new_game_keeps_rules():
    session = draw_all(GameSession(STRICT), "K1 K2")
    fresh = session.new_game()
    assert fresh.rules is STRICT
    assert fresh.events == ()


def test_with_rules_replays_or_rejects():
    session = draw_all(GameSession(), "K3 K4 K5 M4 S8").discard(parse_card("S8"))
    with pytest.raises(IllegalActionError, match="yasak"):
        session.with_rules(STRICT)
    ok = draw_all(GameSession(), "K1 M3 S5 K7 M8").discard(parse_card("K1"))
    assert ok.with_rules(STRICT).state == ok.state


def _random_session(seed: int, rules=RULES) -> GameSession:
    rng = random.Random(seed)
    deck = list(ALL_CARDS)
    rng.shuffle(deck)
    session = GameSession(rules)
    while session.phase is not Phase.FINISHED:
        if session.phase is Phase.AWAITING_DRAW:
            session = session.draw(deck.pop())
        else:
            session = session.act(rng.choice(legal_actions(session.state, rules)))
    return session


@pytest.mark.parametrize("seed", range(50))
def test_undo_walks_back_through_every_state(seed):
    session = _random_session(seed)
    expected = list(session.states)
    assert session.replay() == session.state
    while session.can_undo:
        expected.pop()
        session = session.undo()
        assert session.state == expected[-1]
        assert session.replay() == session.state
    assert session.state == GameState()


@pytest.mark.parametrize("seed", range(50))
def test_branching_after_undo_stays_consistent(seed):
    """Rastgele geri al + farklı eylem dizilerinde önbellek ile yeniden oynatma uyuşur."""
    rng = random.Random(10_000 + seed)
    session = GameSession(RULES)
    for _ in range(300):
        if session.can_undo and rng.random() < 0.3:
            session = session.undo()
        else:
            actions = legal_actions(session.state, RULES)
            if not actions:
                break
            session = session.act(rng.choice(actions))
        state = session.state
        assert session.replay() == state
        assert state == (apply(session.states[-2], session.events[-1], RULES) if session.events else GameState())
        total = (
            state.hand.bit_count()
            + 3 * len(state.played)
            + state.discarded.bit_count()
            + state.deck_remaining
        )
        assert total == 24
        assert state.score == sum(c.points(RULES) for c in state.played)


def test_session_equality_ignores_cache():
    a = draw_all(GameSession(), "K1 K2 K3")
    b = GameSession(RULES, a.events)
    assert a == b
    assert a.states == b.states


def test_describe_discard():
    assert describe_action(Discard(parse_card("S8")), RULES) == "Atıldı: S8"


def test_remove_draw_fixes_wrong_entry():
    session = draw_all(GameSession(), "K1 K2 K3")
    fixed = session.remove_draw(parse_card("K2"))
    assert fixed == draw_all(GameSession(), "K1 K3")
    assert fixed.state.unseen & parse_card("K2").bit


def test_remove_draw_in_full_hand():
    session = draw_all(GameSession(), "K3 K4 K5 M4 S8")
    fixed = session.remove_draw(parse_card("S8")).draw(parse_card("S4"))
    assert set(fixed.state.hand_cards) == set(parse_cards("K3 K4 K5 M4 S4"))


def test_remove_draw_blocked_after_decision():
    session = draw_all(GameSession(), "K3 K4 K5 M4 S8").discard(parse_card("S8"))
    with pytest.raises(IllegalActionError, match="önce onları geri alın"):
        session.remove_draw(parse_card("M4"))
    with pytest.raises(IllegalActionError, match="kart girişi yok"):
        session.remove_draw(parse_card("K1"))
    later = session.draw(parse_card("K1"))
    assert later.remove_draw(parse_card("K1")) == session
