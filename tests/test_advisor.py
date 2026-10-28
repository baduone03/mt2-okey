from okey.advisor import GREEDY_LIMITATION, greedy_recommendation
from okey.cards import mask_of, parse_card, parse_cards
from okey.combos import make_combo
from okey.rules import OFFICIAL_2026
from okey.state import Discard, GameState, Play

RULES = OFFICIAL_2026


def state_of(hand: str, gone: str = "", score: int = 0) -> GameState:
    return GameState(hand=mask_of(parse_cards(hand)), discarded=mask_of(parse_cards(gone)), score=score)


def test_no_recommendation_outside_decision_phase():
    assert greedy_recommendation(GameState(), RULES) is None
    assert greedy_recommendation(state_of("K1 K2"), RULES) is None


def test_play_recommendation_with_explanation():
    rec = greedy_recommendation(state_of("K6 K7 K8 M7 S7"), RULES)
    assert rec.action == Play(make_combo(parse_cards("K6 K7 K8")))
    assert rec.immediate_points == 100
    assert rec.title == "Oyna K6-K7-K8 (+100)"
    assert set(rec.cards) == set(parse_cards("K6 K7 K8"))
    assert any("+100" in p for p in rec.pros)
    assert any("K7-M7-S7 (+80)" in c for c in rec.cons)
    assert GREEDY_LIMITATION in rec.cons


def test_mixed_run_con_mentions_same_color_bonus():
    rec = greedy_recommendation(state_of("K3 M4 S5 K8 M1"), RULES)
    assert rec.action == Play(make_combo(parse_cards("K3 M4 S5")))
    assert any("+40 daha fazla" in c for c in rec.cons)


def test_gold_threshold_pro():
    rec = greedy_recommendation(state_of("K6 K7 K8 M1 S3", score=320), RULES)
    assert any("altın sandık eşiğine" in p for p in rec.pros)
    rec = greedy_recommendation(state_of("K6 K7 K8 M1 S3", score=200), RULES)
    assert not any("altın" in p for p in rec.pros)


def test_discard_recommendation():
    rec = greedy_recommendation(state_of("K3 M5 S7 K8 M1", gone="K1 S1 K2 M2 S2"), RULES)
    assert rec.action == Discard(parse_card("M1"))
    assert rec.immediate_points == 0
    assert rec.title == "At M1"
    assert any("hiçbir üçlü kalmadı" in p for p in rec.pros)


def test_discard_with_live_combos_lists_loss():
    rec = greedy_recommendation(state_of("K1 M3 S5 K7 M8"), RULES)
    assert isinstance(rec.action, Discard)
    assert any("kalıcı olarak kaybolur" in c for c in rec.cons)
