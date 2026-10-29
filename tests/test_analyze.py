import random

from okey.analyze import format_review, review
from okey.cards import ALL_CARDS
from okey.session import GameSession, to_log, from_log
from okey.state import Phase, legal_actions
from okey.strategies import GreedyPolicy


def played_game(seed: int) -> GameSession:
    rng = random.Random(seed)
    deck = list(ALL_CARDS)
    rng.shuffle(deck)
    s = GameSession()
    while s.phase is not Phase.FINISHED:
        if s.phase is Phase.AWAITING_DRAW:
            s = s.draw(deck.pop())
        else:
            s = s.act(GreedyPolicy().choose(s.state, s.rules, rng))
    return s


def test_review_full_game():
    s = played_game(3)
    r = review(from_log(to_log(s)), n_simulations=20)
    assert r.final_score == s.state.score
    assert len(r.draws) == 24
    assert r.oracle_score is not None and r.oracle_score >= r.final_score
    assert len(r.decisions) == sum(1 for e in s.events if e.__class__.__name__ != "Draw")
    for d in r.decisions:
        assert 0.0 <= d.played_p_silver <= 1.0 and 0.0 <= d.best_p_silver <= 1.0
    assert any(d.exact for d in r.decisions)  # oyun sonu kesin hesaplanır
    text = format_review(r)
    assert f"Oyun sonu: {s.state.score} puan" in text
    assert "Kusursuz oyun" in text


def test_review_partial_game_has_no_oracle():
    s = played_game(4)
    partial = GameSession(s.rules, s.events[:9])
    r = review(partial, n_simulations=10)
    assert r.oracle_score is None
    assert "hesaplanamadı" in format_review(r)
