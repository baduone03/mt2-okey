"""3x8 tıklanabilir kart tablosu."""

from __future__ import annotations

import streamlit as st

from okey.board import Zone, card_zone, handle_card_click
from okey.cards import NUMBERS, Card, Color, CardParseError, parse_cards
from okey.state import GameState, Phase

from views import state as ui

COLOR_HEX = {Color.RED: "#d64545", Color.BLUE: "#3a6fd8", Color.YELLOW: "#d9a400"}
TEXT_ON_COLOR = {Color.RED: "#ffffff", Color.BLUE: "#ffffff", Color.YELLOW: "#1f1f1f"}


def _key(card: Card) -> str:
    return f"card-{card.code}"


def _card_css(card: Card, zone: Zone, selected: bool) -> str:
    color = COLOR_HEX[card.color]
    base = f".st-key-{_key(card)} button"
    # Streamlit'in hover/focus stilleri kart rengini ezmesin.
    sel = f"{base}, {base}:hover, {base}:focus, {base}:active, {base}:focus:not(:active)"
    if zone is Zone.HAND:
        rules = (
            f"background:{color};color:{TEXT_ON_COLOR[card.color]};border:2px solid {color};"
            "font-weight:700;"
        )
        if selected:
            rules += "outline:3px solid #2e7d32;outline-offset:2px;transform:translateY(-3px);"
    elif zone is Zone.UNSEEN:
        rules = f"background:transparent;color:{color};border:2px solid {color};font-weight:600;"
    else:  # oynanmış / atılmış
        rules = "opacity:0.35;text-decoration:line-through;"
    important = ";".join(f"{r} !important" for r in rules.split(";") if r)
    return f"{sel}{{{important}}}"


def _on_click(card: Card) -> None:
    ui.apply_click(handle_card_click(ui.session(), ui.selection(), card))


def render() -> None:
    session = ui.session()
    state = session.state
    selection = ui.selection()

    css = [_card_css(card, card_zone(state, card), card in selection) for card in _all_cards()]
    st.html(f"<style>{GRID_CSS}{''.join(css)}</style>")

    with st.container(key="card-grid"):
        _render_rows(state)

    if session.phase is Phase.AWAITING_DRAW:
        _quick_entry()


# Dar ekranlarda Streamlit sütunları alt alta dizer; kart tablosu 3x8 kalmalı.
GRID_CSS = (
    ".st-key-card-grid [data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;gap:0.3rem}"
    ".st-key-card-grid [data-testid='stColumn']{min-width:0 !important;width:auto !important;flex:1 1 0 !important}"
    ".st-key-card-grid button{padding:0.25rem 0 !important;min-height:2.2rem}"
    "@media (max-width:640px){.okey-long{display:none}}"
)


def _render_rows(state: GameState) -> None:
    for color in Color:
        cols = st.columns([1.4] + [1] * len(NUMBERS), vertical_alignment="center")
        cols[0].markdown(
            f"<span style='color:{COLOR_HEX[color]};font-weight:700'>{color.code}"
            f"<span class='okey-long'>{color.label_tr[1:]}</span></span>",
            unsafe_allow_html=True,
        )
        for col, number in zip(cols[1:], NUMBERS):
            card = Card(color, number)
            zone = card_zone(state, card)
            label = str(number) + (" ✓" if zone is Zone.PLAYED else " ✗" if zone is Zone.DISCARDED else "")
            col.button(
                label,
                key=_key(card),
                on_click=_on_click,
                args=(card,),
                width="stretch",
                help=f"{color.label_tr} {number} — {zone.value}",
            )


def _all_cards() -> list[Card]:
    return [Card(color, number) for color in Color for number in NUMBERS]


def _on_quick_entry() -> None:
    text = st.session_state.get("quick_entry", "")
    st.session_state["quick_entry"] = ""
    try:
        cards = parse_cards(text)
    except CardParseError as exc:
        ui.set_message(str(exc))
        return
    session = ui.session()
    for card in cards:
        if session.phase is not Phase.AWAITING_DRAW:
            ui.set_session(session, f"Masa doldu; {card} ve sonrası girilmedi.")
            return
        result = handle_card_click(session, frozenset(), card)
        if result.message:
            ui.set_session(session, result.message)
            return
        session = result.session
    ui.set_session(session)


def _quick_entry() -> None:
    st.text_input(
        "Hızlı giriş",
        key="quick_entry",
        on_change=_on_quick_entry,
        placeholder="ör. K5 M6 S7 (K=kırmızı, M=mavi, S=sarı) ve Enter",
    )
