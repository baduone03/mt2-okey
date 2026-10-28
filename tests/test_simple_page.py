"""Sade oyun ekranının (uygulamanın varsayılan sayfası) başsız uçtan uca testleri."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from okey.cards import parse_card, parse_cards  # noqa: E402
from okey.state import Discard, Phase, Play  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


@pytest.fixture
def at() -> AppTest:
    app = AppTest.from_file(APP, default_timeout=60)
    app.session_state["mc_n"] = 60  # testleri hızlı tut
    app.run()
    assert not app.exception
    return app


def session(at: AppTest):
    return at.session_state["okey_session"]


def tap(at: AppTest, codes: str) -> AppTest:
    for code in codes.split():
        at.button(key=f"card-{code}").click().run()
        assert not at.exception
    return at


def texts(at: AppTest) -> str:
    return " ".join(str(h.proto) for h in at.get("html"))


def test_default_page_is_simple_and_asks_for_cards(at):
    assert "Masadaki kartları işaretle" in texts(at)
    assert "0/5 kart girildi" in texts(at)
    assert not at.metric  # olasılık/metrik yok
    assert not at.dataframe


def test_full_turn_flow(at):
    tap(at, "K3 K4 K5 M4 S8")
    assert session(at).phase is Phase.DECIDE
    page = texts(at)
    assert "OYNA" in page or "AT" in page
    advice = next(iter(at.session_state["okey_advice_cache"].values()))
    best = advice.best.action
    at.button(key="done").click().run()
    s = session(at)
    assert s.events[-1] == best
    assert s.phase is Phase.AWAITING_DRAW
    needed = 3 if isinstance(best, Play) else 1
    assert f"Yerine gelen {needed} kartı işaretle" in texts(at)


def test_tap_on_table_card_removes_wrong_entry_even_when_full(at):
    tap(at, "K3 K4 K5 M4 S8 S8")
    s = session(at)
    assert parse_card("S8") not in s.state.hand_cards
    assert s.phase is Phase.AWAITING_DRAW


def test_other_move(at):
    tap(at, "K3 K4 K5 M4 S8")
    advice = next(iter(at.session_state["okey_advice_cache"].values()))
    options = [r.action for r in advice.recommendations]
    target = Discard(parse_card("S8"))
    at.selectbox(key="other_move").set_value(options.index(target)).run()
    at.button(key="done_other").click().run()
    assert session(at).events[-1] == target


def test_full_table_rejects_new_card_with_hint(at):
    tap(at, "K3 K4 K5 M4 S8")
    at.button(key="card-K1").click().run()
    assert "Yaptım" in at.warning[0].value


def test_undo_and_new_game_confirmation(at):
    tap(at, "K1 K2")
    at.button(key="simple_undo").click().run()
    assert session(at).state.hand_cards == (parse_card("K1"),)
    at.button(key="simple_new").click().run()
    assert session(at).events  # henüz silinmedi, onay bekliyor
    at.button(key="simple_new_yes").click().run()
    assert session(at).events == ()


def test_new_game_can_be_cancelled(at):
    tap(at, "K1")
    at.button(key="simple_new").click().run()
    at.button(key="simple_new_no").click().run()
    assert session(at).events
    assert at.button(key="simple_new")  # tekrar normal düğme


def test_finished_game_message(at):
    s = session(at)
    while s.phase is not Phase.FINISHED:
        if s.phase is Phase.AWAITING_DRAW:
            s = s.draw(s.state.unseen_cards[0])
        else:
            from okey.state import legal_actions

            s = s.act(legal_actions(s.state, s.rules)[0])
    at.session_state["okey_session"] = s
    at.run()
    assert "OYUN BİTTİ" in texts(at)
    assert f"{s.state.score} puan" in texts(at)


def test_used_card_tap_warns(at):
    tap(at, "K6 K7 K8 M1 S3")
    s = session(at).play(parse_cards("K6 K7 K8"))
    at.session_state["okey_session"] = s
    at.run()
    tap(at, "K6")
    assert "Geri al" in at.warning[0].value
