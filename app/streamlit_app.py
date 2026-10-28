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

from views import compare, game_page
from views import state as ui

st.set_page_config(page_title="Metin2 Okey Asistanı", page_icon="🃏", layout="wide")
ui.init()

st.navigation(
    [
        st.Page(game_page.render, title="Oyun", icon="🃏", url_path="oyun", default=True),
        st.Page(compare.render, title="Strateji karşılaştırma", icon="📊", url_path="karsilastirma"),
    ]
).run()
