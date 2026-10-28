"""Hamle geçmişi."""

from __future__ import annotations

import streamlit as st

from okey.session import describe_action

from views import state as ui


def render() -> None:
    session = ui.session()
    history = session.history
    with st.expander(f"Hamle geçmişi ({len(history)})", expanded=False):
        if not history:
            st.caption("Henüz hamle yok.")
            return
        for entry in reversed(history):
            st.markdown(
                f"{entry.index}. {describe_action(entry.action, session.rules)} "
                f"— puan {entry.state_after.score}, destede {entry.state_after.deck_remaining}"
            )
