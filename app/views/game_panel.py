"""Puan, sandık durumu, masa ve hamle seçimi panelleri."""

from __future__ import annotations

import streamlit as st

from okey.board import selected_action
from okey.cards import Card
from okey.combos import combos_in
from okey.rules import Chest
from okey.state import IllegalActionError, Phase, Play

from views import state as ui

CHEST_ICON = {Chest.BRONZE: "🥉", Chest.SILVER: "🥈", Chest.GOLD: "🥇"}


def _cards_text(cards: tuple[Card, ...] | list[Card]) -> str:
    return " ".join(card.code for card in cards) if cards else "—"


def render_metrics() -> None:
    session = ui.session()
    state, rules = session.state, session.rules
    gold = rules.chest_thresholds.gold
    chest = rules.chest_for(state.score)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Puan", state.score)
    c2.metric("Altına kalan", max(0, gold - state.score))
    c3.metric("Destede kalan", state.deck_remaining)
    c4.metric("Şu anki sandık", f"{CHEST_ICON[chest]} {chest.value.capitalize()}")


def render_phase_banner() -> None:
    session = ui.session()
    state, rules = session.state, session.rules
    phase = session.phase
    if phase is Phase.AWAITING_DRAW:
        st.info(
            f"Masaya gelen kartları girin: {state.hand.bit_count()}/{rules.hand_size}. "
            "Yanlış girdiğiniz karta tekrar tıklayarak kaldırabilirsiniz."
        )
    elif phase is Phase.DECIDE:
        st.success("Hamle sırası: oynamak için 3 kart, atmak için 1 kart seçip onaylayın.")
    else:
        chest = rules.chest_for(state.score)
        st.warning(f"Oyun bitti: {state.score} puan — {CHEST_ICON[chest]} {chest.value} sandık.")
    if ui.message():
        st.error(ui.message())


def _confirm(action) -> None:
    ui.set_session(ui.session().act(action))


def _remove_selected(card: Card) -> None:
    try:
        ui.set_session(ui.session().remove_draw(card))
    except IllegalActionError as exc:
        ui.set_message(str(exc))


def render_move_panel() -> None:
    session = ui.session()
    if session.phase is not Phase.DECIDE:
        return
    selection = ui.selection()
    action, explanation = selected_action(session, selection)

    st.subheader("Hamleyi onayla")
    st.caption(f"Seçili: {_cards_text(sorted(selection))} — {explanation}")
    c1, c2 = st.columns(2)
    c1.button(
        "Onayla" if action is None else f"Onayla: {'oyna' if isinstance(action, Play) else 'at'}",
        type="primary",
        disabled=action is None,
        on_click=_confirm,
        args=(action,),
        width="stretch",
        key="confirm_move",
    )
    if len(selection) == 1:
        (card,) = selection
        c2.button(
            f"{card} yanlış girildi, kaldır",
            on_click=_remove_selected,
            args=(card,),
            width="stretch",
            key="remove_selected",
        )

    combos = sorted(
        combos_in(session.state.hand), key=lambda c: -c.points(session.rules)
    )
    if combos:
        st.caption("Masadaki geçerli üçlüler (öneri değildir, sadece liste):")
        for combo in combos:
            st.button(
                f"Oyna {combo} — {combo.kind.value}, +{combo.points(session.rules)}",
                key=f"play-{combo}",
                on_click=_confirm,
                args=(Play(combo),),
            )
    else:
        st.caption("Masada geçerli üçlü yok; bir kart atmanız gerekiyor.")


def render_zones() -> None:
    session = ui.session()
    state, rules = session.state, session.rules
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Masadaki kartlar:** {_cards_text(state.hand_cards)}")
        st.markdown("**Oynanan üçlüler:**")
        if state.played:
            st.dataframe(
                [
                    {"#": i, "Üçlü": str(c), "Tür": c.kind.value, "Puan": c.points(rules)}
                    for i, c in enumerate(state.played, start=1)
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("Henüz yok.")
    with c2:
        st.markdown(f"**Atılan kartlar ({state.discarded.bit_count()}):** {_cards_text(state.discarded_cards)}")
        st.markdown(f"**Görülmemiş kartlar ({state.deck_remaining}):** {_cards_text(state.unseen_cards)}")
