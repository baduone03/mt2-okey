"""Streamlit oturum durumu: GameSession, kart seçimi ve son uyarı mesajı."""

from __future__ import annotations

import streamlit as st

from okey.board import ClickResult
from okey.cards import Card
from okey.rules import OFFICIAL_2026
from okey.session import GameSession

SESSION = "okey_session"
SELECTION = "okey_selection"
MESSAGE = "okey_message"


def init() -> None:
    st.session_state.setdefault(SESSION, GameSession(OFFICIAL_2026))
    st.session_state.setdefault(SELECTION, frozenset())
    st.session_state.setdefault(MESSAGE, None)


def session() -> GameSession:
    return st.session_state[SESSION]


def selection() -> frozenset[Card]:
    return st.session_state[SELECTION]


def message() -> str | None:
    return st.session_state[MESSAGE]


def set_session(new: GameSession, msg: str | None = None) -> None:
    st.session_state[SESSION] = new
    st.session_state[SELECTION] = frozenset()
    st.session_state[MESSAGE] = msg


def apply_click(result: ClickResult) -> None:
    st.session_state[SESSION] = result.session
    st.session_state[SELECTION] = result.selection
    st.session_state[MESSAGE] = result.message


def set_message(msg: str | None) -> None:
    st.session_state[MESSAGE] = msg
