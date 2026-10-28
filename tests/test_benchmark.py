import sys
import types

import pytest

from okey.benchmark import (
    GameResult,
    compare,
    format_markdown,
    run_benchmark,
    run_policy,
    summarize,
)
from okey.cards import FULL_MASK
from okey.rules import OFFICIAL_2026
from okey.simulation import deck_order, play_out, policy_rng
from okey.state import GameState
from okey.strategies import GreedyPolicy, RandomPolicy
from okey.strategies.monte_carlo import MonteCarloPolicy

RULES = OFFICIAL_2026


def test_run_policy_uses_common_decks():
    results = run_policy(GreedyPolicy(), RULES, 20, seed=5)
    assert [r.index for r in results] == list(range(20))
    for r in results:
        expected = play_out(GameState(), RULES, GreedyPolicy(), deck_order(FULL_MASK, 5, r.index), policy_rng(5, r.index))
        assert r.score == expected.score
        assert r.seconds >= 0


def test_parallel_matches_serial(monkeypatch):
    # Önceki testler (Streamlit AppTest) __main__'i değiştirebilir; alt süreçler onu
    # yeniden içe aktarmasın diye temiz bir __main__ kullan.
    monkeypatch.setitem(sys.modules, "__main__", types.ModuleType("__main__"))
    serial = run_policy(RandomPolicy(), RULES, 30, seed=8)
    parallel = run_policy(RandomPolicy(), RULES, 30, seed=8, workers=2)
    assert [r.score for r in serial] == [r.score for r in parallel]


def test_summarize_and_compare():
    a = [GameResult(i, s, 0.01) for i, s in enumerate([400, 300, 250, 410])]
    b = [GameResult(i, s, 0.02) for i, s in enumerate([300, 300, 200, 410])]
    s = summarize("A", a, RULES)
    assert s.n_games == 4
    assert s.gold_rate == 0.5
    assert s.silver_rate == 0.25
    assert s.silver_or_better_rate == 0.75
    assert s.mean_score == 340
    assert s.median_score == 350
    assert s.seconds_per_game == pytest.approx(0.01)
    assert s.gold_ci[0] <= 0.5 <= s.gold_ci[1]
    c = compare("A", a, "B", b, RULES)
    assert c.gold_diff == 0.25
    assert c.silver_or_better_diff == 0.0
    assert c.score_diff == 37.5
    with pytest.raises(ValueError):
        compare("A", a[:3], "B", b, RULES)


def test_run_benchmark_report():
    report = run_benchmark(
        [RandomPolicy(), GreedyPolicy(), MonteCarloPolicy(5)], RULES, n_games=4, seed=1
    )
    names = [s["name"] for s in report["summaries"]]
    assert names == ["Rastgele", "Açgözlü", "Monte Carlo (N=5, devam: Açgözlü)"]
    assert {c["name"] for c in report["comparisons"]} == {"Rastgele", names[2]}
    assert all(len(v) == 4 for v in report["scores"].values())
    md = format_markdown(report)
    assert "| Açgözlü |" in md and "Eşleştirilmiş farklar" in md


def test_invalid_game_count():
    with pytest.raises(ValueError):
        run_policy(GreedyPolicy(), RULES, 0, seed=1)


def test_progress_callback():
    calls = []
    run_benchmark([GreedyPolicy()], RULES, n_games=10, seed=1, progress=lambda *a: calls.append(a))
    assert calls[-1] == ("Açgözlü", 10, 10)
    assert all(name == "Açgözlü" and 0 < done <= 10 for name, done, _ in calls)
