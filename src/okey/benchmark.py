"""Strateji karşılaştırması: aynı deste sıralarında oynanan oyunların istatistikleri.

Kullanım:
    python -m okey.benchmark --games 1000 --seed 2026 --mc-n 100 --workers 4 \\
        --json docs/benchmarks/results.json

Her strateji i'inci oyunda aynı deste sırasını (ve aynı politika tohumunu) kullanır;
böylece stratejiler arasındaki farklar eşleştirilmiş olarak ölçülür.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass

from okey.cards import FULL_MASK
from okey.rules import PRESETS, RuleConfig
from okey.simulation import deck_order, play_out, policy_rng
from okey.state import GameState
from okey.stats import mean_and_se, median, paired_difference, wilson_interval
from okey.strategies.base import Policy
from okey.strategies.greedy import GreedyPolicy
from okey.strategies.monte_carlo import MonteCarloPolicy
from okey.strategies.random_policy import RandomPolicy


@dataclass(frozen=True)
class GameResult:
    index: int
    score: int
    seconds: float


@dataclass(frozen=True)
class PolicySummary:
    name: str
    n_games: int
    gold_rate: float
    gold_ci: tuple[float, float]
    silver_rate: float  # tam gümüş kademesi
    silver_ci: tuple[float, float]
    silver_or_better_rate: float
    mean_score: float
    score_se: float
    median_score: float
    seconds_per_game: float


@dataclass(frozen=True)
class PairedComparison:
    name: str
    baseline: str
    gold_diff: float
    gold_diff_se: float
    silver_or_better_diff: float
    silver_or_better_diff_se: float
    score_diff: float
    score_diff_se: float


def summarize(name: str, results: Sequence[GameResult], rules: RuleConfig) -> PolicySummary:
    scores = [r.score for r in results]
    n = len(scores)
    gold = sum(s >= rules.chest_thresholds.gold for s in scores)
    silver_plus = sum(s >= rules.chest_thresholds.silver for s in scores)
    silver = silver_plus - gold
    mean, se = mean_and_se(scores)
    return PolicySummary(
        name=name,
        n_games=n,
        gold_rate=gold / n,
        gold_ci=wilson_interval(gold, n),
        silver_rate=silver / n,
        silver_ci=wilson_interval(silver, n),
        silver_or_better_rate=silver_plus / n,
        mean_score=mean,
        score_se=se,
        median_score=median(scores),
        seconds_per_game=sum(r.seconds for r in results) / n,
    )


def compare(
    name: str,
    results: Sequence[GameResult],
    baseline: str,
    baseline_results: Sequence[GameResult],
    rules: RuleConfig,
) -> PairedComparison:
    a = sorted(results, key=lambda r: r.index)
    b = sorted(baseline_results, key=lambda r: r.index)
    if [r.index for r in a] != [r.index for r in b]:
        raise ValueError("Karşılaştırılan stratejiler aynı oyunlarda oynanmalı.")
    gold, silver = rules.chest_thresholds.gold, rules.chest_thresholds.silver
    gd, gse = paired_difference([int(r.score >= gold) for r in a], [int(r.score >= gold) for r in b])
    sd, sse = paired_difference([int(r.score >= silver) for r in a], [int(r.score >= silver) for r in b])
    md, mse = paired_difference([r.score for r in a], [r.score for r in b])
    return PairedComparison(name, baseline, gd, gse, sd, sse, md, mse)


def _play_chunk(args: tuple[Policy, RuleConfig, int, list[int]]) -> list[GameResult]:
    policy, rules, seed, indices = args
    results = []
    for i in indices:
        start = time.perf_counter()
        final = play_out(GameState(), rules, policy, deck_order(FULL_MASK, seed, i), policy_rng(seed, i))
        results.append(GameResult(i, final.score, time.perf_counter() - start))
    return results


def run_policy(
    policy: Policy,
    rules: RuleConfig,
    n_games: int,
    seed: int,
    workers: int = 1,
    progress: Callable[[int, int], None] | None = None,
) -> list[GameResult]:
    """Politikayı n_games oyunda oynatır; i'inci oyun her politikada aynı desteyi kullanır.

    workers > 1 alt süreç (spawn) kullanır. Alt süreçler __main__ modülünü yeniden içe
    aktardığından, çağıran betik `if __name__ == "__main__":` korumasına sahip olmalıdır;
    Streamlit gibi __main__'i değiştiren ortamlarda workers=1 kullanın.
    """
    if n_games < 1:
        raise ValueError(f"Oyun sayısı en az 1 olmalı: {n_games}")
    chunk = max(1, min(50, n_games // max(1, workers * 4)))
    batches = [list(range(i, min(i + chunk, n_games))) for i in range(0, n_games, chunk)]
    jobs = [(policy, rules, seed, batch) for batch in batches]
    results: list[GameResult] = []
    if workers <= 1:
        for job in jobs:
            results.extend(_play_chunk(job))
            if progress:
                progress(len(results), n_games)
    else:
        # 'spawn': çok iş parçacıklı süreçlerde (ör. Streamlit) fork kilitlenmesini önler.
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
            for part in pool.map(_play_chunk, jobs):
                results.extend(part)
                if progress:
                    progress(len(results), n_games)
    return sorted(results, key=lambda r: r.index)


def run_benchmark(
    policies: Sequence[Policy],
    rules: RuleConfig,
    n_games: int,
    seed: int,
    workers: int = 1,
    baseline: str | None = None,
    progress: Callable[[str, int, int], None] | None = None,
) -> dict:
    """Tüm politikaları aynı oyunlarda çalıştırır ve özet + eşleştirilmiş farkları döndürür.

    `progress(politika_adı, biten_oyun, toplam_oyun)` her parça bitince çağrılır.
    """
    raw = {}
    for p in policies:
        callback = (lambda done, total, name=p.name: progress(name, done, total)) if progress else None
        raw[p.name] = run_policy(p, rules, n_games, seed, workers, callback)
    baseline = baseline or GreedyPolicy.name
    summaries = [summarize(name, res, rules) for name, res in raw.items()]
    comparisons = [
        compare(name, res, baseline, raw[baseline], rules)
        for name, res in raw.items()
        if baseline in raw and name != baseline
    ]
    return {
        "rules": rules.name,
        "n_games": n_games,
        "seed": seed,
        "summaries": [asdict(s) for s in summaries],
        "comparisons": [asdict(c) for c in comparisons],
        "scores": {name: [r.score for r in res] for name, res in raw.items()},
    }


def _pct(p: float) -> str:
    return f"%{100 * p:.1f}"


def format_markdown(report: dict) -> str:
    lines = [
        f"Kurallar: {report['rules']} · Oyun sayısı: {report['n_games']} · Tohum: {report['seed']}",
        "",
        "| Strateji | Altın | Altın %95 | Gümüş | Gümüş %95 | Ortalama ± SH | Medyan | sn/oyun |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in report["summaries"]:
        lines.append(
            f"| {s['name']} | {_pct(s['gold_rate'])} | {_pct(s['gold_ci'][0])}–{_pct(s['gold_ci'][1])} "
            f"| {_pct(s['silver_rate'])} | {_pct(s['silver_ci'][0])}–{_pct(s['silver_ci'][1])} "
            f"| {s['mean_score']:.1f} ± {s['score_se']:.1f} | {s['median_score']:.0f} "
            f"| {s['seconds_per_game']:.4f} |"
        )
    if report["comparisons"]:
        lines += [
            "",
            "Eşleştirilmiş farklar (aynı desteler; ± 1,96 × standart hata):",
            "",
            "| Strateji − Referans | Altın farkı | Gümüş-veya-üstü farkı | Ortalama puan farkı |",
            "|---|---|---|---|",
        ]
        for c in report["comparisons"]:
            lines.append(
                f"| {c['name']} − {c['baseline']} "
                f"| {100 * c['gold_diff']:+.1f} ± {196 * c['gold_diff_se']:.1f} puan "
                f"| {100 * c['silver_or_better_diff']:+.1f} ± {196 * c['silver_or_better_diff_se']:.1f} puan "
                f"| {c['score_diff']:+.1f} ± {1.96 * c['score_diff_se']:.1f} |"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Okey stratejilerini aynı destelerde karşılaştırır.")
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--mc-n", type=int, default=100, help="Monte Carlo için aday başına simülasyon (0: MC yok)")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--rules", choices=sorted(PRESETS), default="official_2026")
    parser.add_argument("--json", help="Ham sonuçların yazılacağı JSON dosyası")
    args = parser.parse_args(argv)

    policies: list[Policy] = [RandomPolicy(), GreedyPolicy()]
    if args.mc_n > 0:
        policies.append(MonteCarloPolicy(args.mc_n))
    report = run_benchmark(policies, PRESETS[args.rules], args.games, args.seed, args.workers)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False)
    print(format_markdown(report))


if __name__ == "__main__":
    main()
