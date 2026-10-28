"""Hamle önerisi paneli."""

from __future__ import annotations

import streamlit as st

from okey.advisor import Recommendation, greedy_recommendation

from views import state as ui


def _select(rec: Recommendation) -> None:
    st.session_state[ui.SELECTION] = frozenset(rec.cards)
    ui.set_message(None)


def render() -> None:
    session = ui.session()
    rec = greedy_recommendation(session.state, session.rules)
    if rec is None:
        return
    with st.container(border=True, key="recommendation"):
        st.markdown(f"#### Önerilen hamle: {rec.title}")
        st.caption(f"Strateji: {rec.strategy}")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Avantajlar**")
            for text in rec.pros:
                st.markdown(f"- {text}")
        with c2:
            st.markdown("**Dezavantajlar**")
            for text in rec.cons:
                st.markdown(f"- {text}")
        st.caption(
            "Altın/gümüş sandık olasılıkları ve beklenen puan, Monte Carlo aşamasında "
            "eklenecek; şu an tahmin gösterilmiyor."
        )
        st.button("Öneriyi seç", key="select_recommendation", on_click=_select, args=(rec,))
