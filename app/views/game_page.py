"""Oyun sayfası: kart girişi, öneriler, hamle onayı ve geçmiş."""

from __future__ import annotations

import streamlit as st

from views import card_grid, game_panel, history, recommendations, sidebar


def render() -> None:
    st.title("🃏 Metin2 Okey Asistanı")
    st.caption("Kartlar elle girilir. Uygulama oyuna bağlanmaz ve otomasyon yapmaz.")
    sidebar.render()
    game_panel.render_metrics()
    game_panel.render_phase_banner()
    card_grid.render()
    recommendations.render()
    game_panel.render_move_panel()
    game_panel.render_zones()
    history.render()
