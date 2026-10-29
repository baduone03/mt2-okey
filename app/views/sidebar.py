"""Kenar çubuğu: geri al, yeni oyun ve kural ayarları."""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from okey.rules import PRESETS, UNVERIFIED_RULES
from okey.session import NothingToUndoError
from okey.state import IllegalActionError

from views import state as ui


def _undo() -> None:
    try:
        ui.set_session(ui.session().undo())
    except NothingToUndoError as exc:
        ui.set_message(str(exc))


def _new_game() -> None:
    ui.set_session(ui.session().new_game())


def _change_rules() -> None:
    preset = PRESETS[st.session_state["rules_preset"]]
    rules = replace(preset, discard_requires_no_combo=st.session_state["rules_strict_discard"])
    try:
        ui.set_session(ui.session().with_rules(rules))
    except IllegalActionError as exc:
        # Geçersiz kural değişikliğinde arayüzü eski kurallarla senkron tut.
        old = ui.session().rules
        st.session_state["rules_strict_discard"] = old.discard_requires_no_combo
        ui.set_message(f"Kurallar değiştirilemedi, mevcut hamle geçmişiyle uyumsuz: {exc}")


def render() -> None:
    session = ui.session()
    with st.sidebar:
        st.header("Oyun")
        c1, c2 = st.columns(2)
        c1.button("↶ Geri al", on_click=_undo, disabled=not session.can_undo, width="stretch")
        c2.button("Yeni oyun", on_click=_new_game, width="stretch")

        st.header("Simülasyon")
        st.radio(
            "Yöntem",
            options=["mc", "pimc"],
            format_func={"mc": "Monte Carlo", "pimc": "Kahin planı (deneysel)"}.get,
            key="advice_method",
            help=(
                "Kahin planı deneyseldir: iki bağımsız ölçümde Monte Carlo'dan anlamlı bir farkı "
                "çıkmadı (docs/BENCHMARKS.md). Aşağıdaki ayarlar yalnızca Monte Carlo içindir."
            ),
        )
        st.select_slider(
            "Aday başına simülasyon",
            options=[100, 250, 500, 1000, 2000],
            value=500,
            key="mc_n",
            help="Daha fazla simülasyon belirsizliği azaltır ama hesaplamayı yavaşlatır.",
        )
        st.radio(
            "Devam stratejisi",
            options=["greedy_max", "greedy", "selective"],
            format_func={
                "greedy_max": "Açgözlü, en değerli üçlü (önerilen)",
                "greedy": "Açgözlü, toplam değer",
                "selective": "Seçici (≥50)",
            }.get,
            key="mc_rollout",
            help=(
                "Her aday hamleden sonra oyunun devamı bu stratejiyle simüle edilir. "
                "Önerilen seçenek, 2.000 oyunda gümüş oranını ve ortalama puanı artırdı ve "
                "erken 8 atmalarını yarıdan fazla azalttı (docs/BENCHMARKS.md)."
            ),
        )

        st.header("Kurallar")
        st.selectbox(
            "Kural seti",
            options=list(PRESETS),
            format_func=lambda key: PRESETS[key].name,
            key="rules_preset",
            on_change=_change_rules,
        )
        st.toggle(
            "Üçlü varken kart atmak yasak",
            value=session.rules.discard_requires_no_combo,
            key="rules_strict_discard",
            on_change=_change_rules,
            help="Oyunda doğrulandı: üçlü varken de kart atılabiliyor (docs/RULES.md A6). Kapalı kalmalı.",
        )
        with st.expander("Kural varsayımları"):
            for name, text in UNVERIFIED_RULES.items():
                st.markdown(f"- `{name}`: {text}")
