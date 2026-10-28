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


# --- Monte Carlo önerileri ---

from okey.advisor import MC_STRATEGY, decision_seed, recommend  # noqa: E402
from okey.cards import FULL_MASK  # noqa: E402
from okey.state import legal_actions  # noqa: E402


def endgame(hand: str, unseen: str, score: int) -> GameState:
    hand_mask = mask_of(parse_cards(hand))
    rest = FULL_MASK & ~hand_mask & ~mask_of(parse_cards(unseen))
    return GameState(hand=hand_mask, discarded=rest, score=score)


def test_recommend_none_outside_decision_phase():
    assert recommend(GameState(), RULES) is None


def test_recommend_beats_greedy_in_silver_trap():
    state = endgame("K2 K4 M5 S2 S6", "K3 K8 S1 S7", 240)
    advice = recommend(state, RULES, n_simulations=100)
    best = advice.best
    assert best.strategy == MC_STRATEGY
    assert best.action == Discard(parse_card("M5"))
    assert not best.is_greedy_choice
    assert best.estimate.p_silver_or_better == 1.0
    assert any(
        "Açgözlü seçime (K4-M5-S6, +40) göre:" in p and "%0.0 → %100.0" in p and "290 → " in p
        for p in best.pros
    )
    greedy = [r for r in advice.recommendations if r.is_greedy_choice]
    assert len(greedy) == 1 and greedy[0].action == Play(make_combo(parse_cards("K4 M5 S6")))
    assert advice.evaluation.exact


def test_recommend_covers_all_legal_actions_and_is_reproducible():
    state = state_of("K3 K4 K5 M4 S8")
    advice = recommend(state, RULES, n_simulations=40)
    assert {r.action for r in advice.recommendations} == set(legal_actions(state, RULES))
    assert all(r.estimate.n == 40 for r in advice.recommendations)
    assert recommend(state, RULES, n_simulations=40) == advice
    assert advice.evaluation.seed == decision_seed(state)
    assert advice.recommendations[0].tied_with_best


def test_discard_with_combo_on_table_is_explained():
    state = state_of("K3 K4 K5 M4 S8")
    advice = recommend(state, RULES, n_simulations=20)
    rec = next(r for r in advice.recommendations if r.action == Discard(parse_card("S8")))
    assert any("puan alınmaz" in c for c in rec.cons)
