"""Streamlit arayüzünün başsız (headless) uçtan uca testleri."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from okey.cards import parse_card, parse_cards  # noqa: E402
from okey.state import Phase  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


@pytest.fixture
def at() -> AppTest:
    app = AppTest.from_file(APP, default_timeout=10).run()
    assert not app.exception
    return app


def session(at: AppTest):
    return at.session_state["okey_session"]


def click(at: AppTest, codes: str) -> AppTest:
    for code in codes.split():
        at.button(key=f"card-{code}").click().run()
        assert not at.exception
    return at


def test_initial_render(at):
    assert at.title[0].value.endswith("Metin2 Okey Asistanı")
    assert len([b for b in at.button if b.key and b.key.startswith("card-")]) == 24
    assert session(at).phase is Phase.AWAITING_DRAW
    assert "0/5" in at.info[0].value


def test_enter_cards_play_and_undo(at):
    click(at, "K3 K4 K5 M4 S8")
    assert session(at).phase is Phase.DECIDE
    click(at, "K3 K4 K5")
    assert at.session_state["okey_selection"] == frozenset(parse_cards("K3 K4 K5"))
    at.button(key="confirm_move").click().run()
    state = session(at).state
    assert state.score == 70
    assert set(state.hand_cards) == set(parse_cards("M4 S8"))
    assert at.metric[0].value == "70"

    at.sidebar.button[0].click().run()  # Geri al
    assert session(at).state.score == 0
    assert session(at).phase is Phase.DECIDE


def test_second_click_removes_wrong_entry(at):
    click(at, "K1 K2 K1")
    assert session(at).state.hand_cards == (parse_card("K2"),)


def test_played_card_click_shows_error(at):
    click(at, "K3 K4 K5 M4 S8 K3 K4 K5")
    at.button(key="confirm_move").click().run()
    click(at, "K3")
    assert "zaten oynandı" in at.error[0].value


def test_quick_entry(at):
    at.text_input(key="quick_entry").input("K1 m2 S3").run()
    assert set(session(at).state.hand_cards) == set(parse_cards("K1 M2 S3"))
    at.text_input(key="quick_entry").input("X9").run()
    assert at.error and "renk kodu" in at.error[0].value


def test_listed_combo_button_plays(at):
    click(at, "K6 K7 K8 M1 S2")
    at.button(key="play-K6-K7-K8").click().run()
    assert session(at).state.score == 100


def test_discard_via_selection(at):
    click(at, "K1 M3 S5 K7 M8 K1")
    at.button(key="confirm_move").click().run()
    assert session(at).state.discarded_cards == (parse_card("K1"),)


def test_strict_rule_toggle_rejected_when_history_conflicts(at):
    click(at, "K3 K4 K5 M4 S8 S8")
    at.button(key="confirm_move").click().run()  # üçlü varken S8 atıldı
    at.toggle(key="rules_strict_discard").set_value(True).run()
    assert "Kurallar değiştirilemedi" in at.error[0].value
    assert session(at).rules.discard_requires_no_combo is False
    assert at.toggle(key="rules_strict_discard").value is False


def test_new_game(at):
    click(at, "K1 K2")
    at.sidebar.button[1].click().run()
    assert session(at).events == ()
