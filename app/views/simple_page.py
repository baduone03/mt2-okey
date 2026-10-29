"""Sade oyun ekranı: kartları işaretle, tek bir komut al, "Yaptım"a bas.

Olasılık, tablo veya açıklama göstermez; ayrıntılar "Detaylı" sayfasındadır.
"""

from __future__ import annotations

import html

import streamlit as st

from okey.board import cards_needed
from okey.cards import Card
from okey.rules import Chest
from okey.session import NothingToUndoError, to_log
from okey.state import Action, Phase, Play

from views import state as ui
from views.card_grid import COLOR_HEX, TEXT_ON_COLOR, render as render_grid
from views.recommendations import get_advice

# Sade ekranda doğrulanmış Monte Carlo yöntemi; doğruluk için karar başına 500 simülasyon.
SIMPLE_N = 500
CONFIRM_NEW = "okey_confirm_new"
CHEST_TEXT = {Chest.BRONZE: "🥉 Bronz sandık", Chest.SILVER: "🥈 Gümüş sandık", Chest.GOLD: "🥇 Altın sandık"}

CSS = """
<style>
.okey-cmd{border:2px solid #2e7d32;border-radius:14px;padding:14px 16px;margin:4px 0 10px;
  background:rgba(46,125,50,0.08);text-align:center}
.okey-cmd.okey-wait{border-color:#3a6fd8;background:rgba(58,111,216,0.08)}
.okey-cmd.okey-end{border-color:#d9a400;background:rgba(217,164,0,0.10)}
.okey-verb{font-size:1.6rem;font-weight:800;letter-spacing:0.04em;margin-bottom:8px}
.okey-sub{font-size:1rem;opacity:0.8;margin-top:8px}
.okey-chip{display:inline-block;min-width:2.6rem;padding:8px 10px;margin:0 4px;border-radius:8px;
  font-size:1.4rem;font-weight:800}
.okey-status{font-size:0.95rem;opacity:0.85;margin-bottom:6px}
</style>
"""


def _chip(card: Card) -> str:
    label = f"{card.color.label_tr} {card.number}"
    return (
        f"<span class='okey-chip' title='{html.escape(label)}' aria-label='{html.escape(label)}' "
        f"style='background:{COLOR_HEX[card.color]};color:{TEXT_ON_COLOR[card.color]}'>{card.number}</span>"
    )


def _box(kind: str, verb: str, body: str = "", sub: str = "") -> None:
    st.html(
        f"<div class='okey-cmd {kind}'><div class='okey-verb'>{verb}</div>"
        f"<div>{body}</div>{f'<div class=okey-sub>{sub}</div>' if sub else ''}</div>"
    )


def _describe(action: Action, rules) -> str:
    if isinstance(action, Play):
        return f"Oynadım: {action.combo} (+{action.combo.points(rules)})"
    return f"Attım: {action.card}"


def _do(action: Action) -> None:
    ui.set_session(ui.session().act(action))


def _undo() -> None:
    try:
        ui.set_session(ui.session().undo())
    except NothingToUndoError as exc:
        ui.set_message(str(exc))


def _new_game(confirmed: bool) -> None:
    if confirmed:
        ui.set_session(ui.session().new_game())
        st.session_state[CONFIRM_NEW] = False
    else:
        st.session_state[CONFIRM_NEW] = True


def _cancel_new() -> None:
    st.session_state[CONFIRM_NEW] = False


def _other_move(options: list[Action]) -> None:
    index = st.session_state.get("other_move", 0)
    _do(options[index])


def render() -> None:
    st.html(CSS)
    session = ui.session()
    state, rules, phase = session.state, session.rules, session.phase
    gold = rules.chest_thresholds.gold

    st.markdown("### 🃏 Okey Asistanı")
    st.html(
        f"<div class='okey-status'>Puan <b>{state.score}</b> · Altına kalan "
        f"<b>{max(0, gold - state.score)}</b> · Destede <b>{state.deck_remaining}</b> kart</div>"
    )

    highlight: frozenset[Card] = frozenset()
    advice = None
    if phase is Phase.FINISHED:
        chest = rules.chest_for(state.score)
        _box("okey-end", "OYUN BİTTİ", f"<b>{state.score} puan</b>", CHEST_TEXT[chest])
    elif phase is Phase.AWAITING_DRAW:
        needed = cards_needed(session)
        first_deal = not state.played and not state.discarded
        if first_deal:
            verb = "Masadaki kartları işaretle"
            sub = f"{state.hand.bit_count()}/{rules.hand_size} kart girildi"
        else:
            verb = f"Yerine gelen {needed} kartı işaretle"
            sub = "Yanlış girdiğin karta tekrar dokunarak silebilirsin"
        _box("okey-wait", verb, "", sub)
    else:
        advice = get_advice(SIMPLE_N, method="mc")
        best = advice.best
        highlight = frozenset(best.cards)
        chips = "".join(_chip(c) for c in best.cards)
        if isinstance(best.action, Play):
            _box("", "OYNA", chips, f"+{best.immediate_points} puan")
        else:
            _box("", "AT", chips)
        st.button("✓ Yaptım", type="primary", width="stretch", key="done", on_click=_do, args=(best.action,))

    if ui.message():
        st.warning(ui.message())

    render_grid(simple=True, highlight=highlight)

    if advice is not None:
        options = [rec.action for rec in advice.recommendations]
        with st.expander("Başka bir hamle yaptım"):
            st.selectbox(
                "Oyunda ne yaptın?",
                options=range(len(options)),
                format_func=lambda i: _describe(options[i], rules),
                key="other_move",
            )
            st.button("Bunu yaptım", key="done_other", on_click=_other_move, args=(options,))

    if session.events:
        finished = phase is Phase.FINISHED
        with st.expander("Oyun kaydı", expanded=finished):
            st.caption(
                "Bu kaydı kopyalayıp paylaşırsan oyun adım adım analiz edilebilir "
                "(+ = gelen kart, O = oynanan üçlü, A = atılan kart)."
            )
            st.code(to_log(session), language=None, wrap_lines=True)

    c1, c2 = st.columns(2)
    c1.button("↶ Geri al", key="simple_undo", on_click=_undo, disabled=not session.can_undo, width="stretch")
    if st.session_state.get(CONFIRM_NEW):
        c2.button("Evet, yeni oyun", key="simple_new_yes", type="primary", on_click=_new_game, args=(True,), width="stretch")
        st.button("Vazgeç", key="simple_new_no", on_click=_cancel_new, width="stretch")
    else:
        c2.button("Yeni oyun", key="simple_new", on_click=_new_game, args=(False,), width="stretch")
