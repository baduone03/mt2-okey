"""Hamle önerileri paneli (Monte Carlo)."""

from __future__ import annotations

import streamlit as st

from okey.advisor import Advice, Recommendation, recommend

from views import state as ui

MC_N = "mc_n"
_CACHE = "okey_advice_cache"


def _select(rec: Recommendation) -> None:
    st.session_state[ui.SELECTION] = frozenset(rec.cards)
    ui.set_message(None)


def _pct(p: float) -> str:
    return f"%{100 * p:.1f}"


def _interval(ci: tuple[float, float]) -> str:
    return f"{_pct(ci[0])} – {_pct(ci[1])}"


def _advice() -> Advice | None:
    session = ui.session()
    n = st.session_state.get(MC_N, 500)
    key = (session.state, session.rules, n)
    cache = st.session_state.setdefault(_CACHE, {})
    if key not in cache:
        with st.spinner(f"{n} simülasyonla hamleler değerlendiriliyor…"):
            cache.clear()  # yalnızca son karar anını sakla
            cache[key] = recommend(session.state, session.rules, n)
    return cache[key]


def render() -> None:
    advice = _advice()
    if advice is None:
        return
    ev = advice.evaluation
    best = advice.best
    est = best.estimate

    with st.container(border=True, key="recommendation"):
        st.markdown(f"#### Önerilen hamle: {best.title}")
        st.caption(f"Strateji: {best.strategy} — devam stratejisi: {ev.rollout_policy}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Altın sandık", _pct(est.p_gold), help=f"%95 aralık: {_interval(est.gold_ci)}")
        c2.metric("Gümüş sandık", _pct(est.p_silver), help=f"%95 aralık: {_interval(est.silver_ci)}")
        c3.metric("Beklenen puan", f"{est.mean_score:.0f}", help=f"± {1.96 * est.score_se:.1f} (%95)")
        c4.metric("Medyan puan", f"{est.median_score:.0f}")
        st.caption(
            f"Altın %95 aralık: {_interval(est.gold_ci)} · Gümüş %95 aralık: {_interval(est.silver_ci)} · "
            f"Beklenen puan ± {1.96 * est.score_se:.1f}"
        )
        a, b = st.columns(2)
        with a:
            st.markdown("**Avantajlar**")
            for text in best.pros:
                st.markdown(f"- {text}")
        with b:
            st.markdown("**Dezavantajlar**")
            for text in best.cons or ("Belirgin bir dezavantaj bulunmadı.",):
                st.markdown(f"- {text}")
        st.button("Öneriyi seç", key="select_recommendation", on_click=_select, args=(best,))

    if ev.exact:
        method = (
            f"Kalan {ui.session().state.deck_remaining} kartın tüm {ev.n_simulations} sırası denendi; "
            f"sonuçlar devam stratejisine ({ev.rollout_policy}) göre kesindir."
        )
    else:
        method = (
            f"{ev.n_simulations} rastgele deste sırası; tüm adaylar aynı sıralarla değerlendirildi. "
            "Aralıklar %95 Wilson aralığıdır."
        )
    st.caption(
        f"{method} Tahminler kesin olasılık değildir ve doğrulanmamış kural varsayımlarına "
        "bağlıdır (kenar çubuğuna bakın)."
    )

    rows = []
    for rank, rec in enumerate(advice.recommendations, start=1):
        e = rec.estimate
        rows.append(
            {
                "#": rank,
                "Hamle": rec.title,
                "Anlık": rec.immediate_points,
                "P(altın)": _pct(e.p_gold),
                "Altın %95": _interval(e.gold_ci),
                "P(gümüş)": _pct(e.p_silver),
                "Beklenen": f"{e.mean_score:.0f} ± {1.96 * e.score_se:.0f}",
                "Medyan": f"{e.median_score:.0f}",
                "N": e.n,
                "Not": ", ".join(
                    t
                    for t, on in (
                        ("açgözlü", rec.is_greedy_choice),
                        ("≈ en iyi", rec.tied_with_best and rank > 1),
                    )
                    if on
                ),
            }
        )
    with st.expander(f"Tüm adaylar ({len(rows)})", expanded=True):
        st.dataframe(rows, hide_index=True, width="stretch")
        details = st.selectbox(
            "Aday ayrıntısı",
            options=range(len(advice.recommendations)),
            format_func=lambda i: advice.recommendations[i].title,
            key="candidate_detail",
        )
        rec = advice.recommendations[details]
        for text in rec.pros:
            st.markdown(f"- ✅ {text}")
        for text in rec.cons:
            st.markdown(f"- ⚠️ {text}")
        st.button("Bu adayı seç", key="select_candidate", on_click=_select, args=(rec,))
