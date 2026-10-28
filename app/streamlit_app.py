"""Metin2 Okey asistanı — Streamlit giriş noktası.

Çalıştırma: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import okey  # noqa: F401
except ModuleNotFoundError:  # paket kurulmadan doğrudan depodan çalıştırma
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

from views import card_grid, game_panel, history, sidebar
from views import state as ui

st.set_page_config(page_title="Metin2 Okey Asistanı", page_icon="🃏", layout="wide")
ui.init()

st.title("🃏 Metin2 Okey Asistanı")
st.caption("Kartlar elle girilir. Uygulama oyuna bağlanmaz ve otomasyon yapmaz.")

sidebar.render()
game_panel.render_metrics()
game_panel.render_phase_banner()
card_grid.render()
game_panel.render_move_panel()
game_panel.render_zones()
history.render()
