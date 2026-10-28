"""Strateji karşılaştırma sayfası: kayıtlı benchmark raporları ve yeni çalıştırma."""

from __future__ import annotations

import json
import os
from pathlib import Path

import altair as alt
import streamlit as st

from okey.benchmark import run_benchmark
from okey.rules import PRESETS
from okey.strategies import GreedyPolicy, RandomPolicy
from okey.strategies.monte_carlo import MonteCarloPolicy

from views import state as ui

REPORT_DIR = Path(__file__).resolve().parents[2] / "docs" / "benchmarks"
LIVE_REPORT = "okey_live_report"

# Doğrulanmış kategorik paletin ilk üç rengi; renk stratejiye bağlıdır, sıraya değil.
STRATEGY_COLORS = {"Rastgele": "#2a78d6", "Açgözlü": "#eb6834", "Monte Carlo": "#1baf7a"}


def _color(name: str) -> str:
    for prefix, color in STRATEGY_COLORS.items():
        if name.startswith(prefix):
            return color
    return "#8a8984"


def _pct(p: float) -> str:
    return f"%{100 * p:.1f}"


def _stored_reports() -> dict[str, Path]:
    if not REPORT_DIR.is_dir():
        return {}
    return {p.stem: p for p in sorted(REPORT_DIR.glob("*.json"))}


def _summary_rows(report: dict) -> list[dict]:
    return [
        {
            "Strateji": s["name"],
            "Altın": _pct(s["gold_rate"]),
            "Altın %95": f"{_pct(s['gold_ci'][0])} – {_pct(s['gold_ci'][1])}",
            "Gümüş": _pct(s["silver_rate"]),
            "Gümüş %95": f"{_pct(s['silver_ci'][0])} – {_pct(s['silver_ci'][1])}",
            "Ortalama": f"{s['mean_score']:.1f} ± {1.96 * s['score_se']:.1f}",
            "Medyan": f"{s['median_score']:.0f}",
            "sn/oyun": f"{s['seconds_per_game']:.4f}",
            "Oyun": s["n_games"],
        }
        for s in report["summaries"]
    ]


def _comparison_rows(report: dict) -> list[dict]:
    return [
        {
            "Strateji − referans": f"{c['name']} − {c['baseline']}",
            "Altın farkı": f"{100 * c['gold_diff']:+.1f} ± {196 * c['gold_diff_se']:.1f} puan",
            "Gümüş-veya-üstü farkı": f"{100 * c['silver_or_better_diff']:+.1f} ± {196 * c['silver_or_better_diff_se']:.1f} puan",
            "Ortalama puan farkı": f"{c['score_diff']:+.1f} ± {1.96 * c['score_diff_se']:.1f}",
        }
        for c in report["comparisons"]
    ]


def _rate_chart(report: dict, key: str, ci_key: str, title: str) -> alt.Chart:
    names = [s["name"] for s in report["summaries"]]
    data = [
        {
            "Strateji": s["name"],
            "Oran": s[key],
            "Alt": s[ci_key][0],
            "Üst": s[ci_key][1],
            "Etiket": f"{_pct(s[key])} ({_pct(s[ci_key][0])}–{_pct(s[ci_key][1])})",
        }
        for s in report["summaries"]
    ]
    color = alt.Color(
        "Strateji:N",
        scale=alt.Scale(domain=names, range=[_color(n) for n in names]),
        legend=None,  # eksen etiketleri stratejiyi zaten adlandırır
    )
    y = alt.Y("Strateji:N", sort=names, title=None)
    tooltip = [alt.Tooltip("Strateji:N"), alt.Tooltip("Etiket:N", title=title)]
    base = alt.Chart(alt.Data(values=data))
    bars = base.mark_bar(cornerRadiusEnd=4, height=18).encode(
        x=alt.X("Oran:Q", axis=alt.Axis(format="%", grid=True, gridOpacity=0.4), title=title),
        y=y,
        color=color,
        tooltip=tooltip,
    )
    ci = base.mark_rule(strokeWidth=2, color="#52514e").encode(x="Alt:Q", x2="Üst:Q", y=y, tooltip=tooltip)
    labels = base.mark_text(align="left", dx=6, color="#52514e").encode(
        x="Üst:Q", y=y, text="Etiket:N"
    )
    return (bars + ci + labels).properties(height=40 * len(names) + 20)


def _score_chart(report: dict) -> alt.VConcatChart:
    """Strateji başına bir puan histogramı (küçük çoklu grafikler) ve sandık eşikleri."""
    names = list(report["scores"])
    rules = next((r for r in PRESETS.values() if r.name == report["rules"]), None)
    charts = []
    for name in names:
        scores = report["scores"][name]
        data = alt.Data(values=[{"Puan": v, "pay": 1 / len(scores)} for v in scores])
        hist = (
            alt.Chart(data)
            .mark_bar(color=_color(name), cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
            .encode(
                x=alt.X("Puan:Q", bin=alt.Bin(step=20), title="Oyun sonu puanı",
                        scale=alt.Scale(domain=[0, 600])),
                y=alt.Y("sum(pay):Q", axis=alt.Axis(format="%", gridOpacity=0.4), title="Oyun payı"),
                tooltip=[
                    alt.Tooltip("Puan:Q", bin=alt.Bin(step=20), title="Puan aralığı"),
                    alt.Tooltip("sum(pay):Q", format=".1%", title="Oyun payı"),
                ],
            )
        )
        layers = [hist]
        if rules is not None:
            marks = alt.Data(values=[
                {"x": rules.chest_thresholds.silver, "Eşik": "Gümüş"},
                {"x": rules.chest_thresholds.gold, "Eşik": "Altın"},
            ])
            layers.append(
                alt.Chart(marks)
                .mark_rule(strokeDash=[4, 3], color="#52514e", strokeWidth=1.5)
                .encode(x="x:Q", tooltip=["Eşik:N", alt.Tooltip("x:Q", title="Puan")])
            )
        charts.append(alt.layer(*layers).properties(height=120, width="container", title=name))
    return alt.vconcat(*charts)


def _render_report(report: dict, label: str) -> None:
    st.markdown(
        f"**{label}** — kurallar: {report['rules']}, oyun sayısı: {report['n_games']}, "
        f"tohum: {report['seed']}. Tüm stratejiler aynı deste sıralarında oynadı."
    )
    st.dataframe(_summary_rows(report), hide_index=True, width="stretch")
    if report["comparisons"]:
        st.caption("Eşleştirilmiş farklar (aynı desteler, ± 1,96 × standart hata):")
        st.dataframe(_comparison_rows(report), hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    c1.altair_chart(_rate_chart(report, "gold_rate", "gold_ci", "Altın sandık oranı"), width="stretch")
    c2.altair_chart(_rate_chart(report, "silver_rate", "silver_ci", "Gümüş sandık oranı"), width="stretch")
    st.markdown("**Puan dağılımı** (kesikli çizgiler: gümüş ve altın eşikleri)")
    st.altair_chart(_score_chart(report), width="stretch")


def _run_live(n_games: int, seed: int, mc_n: int) -> None:
    session_rules = ui.session().rules
    policies = [RandomPolicy(), GreedyPolicy()]
    if mc_n > 0:
        policies.append(MonteCarloPolicy(mc_n))
    bar = st.progress(0.0, text="Başlıyor…")
    total = n_games * len(policies)
    finished: dict[str, int] = {}

    def progress(name: str, done: int, n: int) -> None:
        finished[name] = done
        bar.progress(sum(finished.values()) / total, text=f"{name}: {done}/{n} oyun")

    workers = max(1, min(4, os.cpu_count() or 1))
    st.session_state[LIVE_REPORT] = run_benchmark(
        policies, session_rules, n_games, seed, workers=workers, progress=progress
    )
    bar.empty()


def render() -> None:
    st.title("📊 Strateji karşılaştırma")
    st.caption(
        "Rastgele, açgözlü ve Monte Carlo stratejileri aynı rastgele deste sıralarında "
        "oynatılır. Oranlar tahmindir; %95 aralıklar örneklem belirsizliğini gösterir."
    )

    tab_saved, tab_live = st.tabs(["Kayıtlı sonuçlar", "Yeni çalıştırma"])
    with tab_saved:
        reports = _stored_reports()
        if not reports:
            st.info("Kayıtlı benchmark bulunamadı (docs/benchmarks/*.json).")
        else:
            names = list(reports)
            default = next((i for i, n in enumerate(names) if n.startswith("main_")), 0)
            choice = st.selectbox("Rapor", names, index=default, key="saved_report")
            report = json.loads(reports[choice].read_text(encoding="utf-8"))
            _render_report(report, choice)

    with tab_live:
        st.markdown(
            "Mevcut kural ayarlarıyla (kenar çubuğu → Oyun sayfası) küçük bir karşılaştırma "
            "çalıştırır. Monte Carlo oyun başına yaklaşık N/100 saniye sürer."
        )
        with st.form("live_benchmark"):
            c1, c2, c3 = st.columns(3)
            n_games = c1.number_input("Oyun sayısı", min_value=10, max_value=5000, value=200, step=50)
            seed = c2.number_input("Tohum", min_value=0, value=2026, step=1)
            mc_n = c3.select_slider("Monte Carlo N (0 = yok)", options=[0, 25, 50, 100, 200], value=0)
            submitted = st.form_submit_button("Çalıştır", type="primary")
        if submitted:
            _run_live(int(n_games), int(seed), int(mc_n))
        if LIVE_REPORT in st.session_state:
            _render_report(st.session_state[LIVE_REPORT], "Son çalıştırma")
