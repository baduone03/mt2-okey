"""Strateji karşılaştırma sayfasının başsız testleri."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SCRIPT = f"""
import sys
sys.path[:0] = [{str(ROOT / "src")!r}, {str(ROOT / "app")!r}]
from views import compare
from views import state as ui
ui.init()
compare.render()
"""


@pytest.fixture
def at() -> AppTest:
    app = AppTest.from_string(SCRIPT, default_timeout=120).run()
    assert not app.exception
    return app


def test_page_renders(at):
    assert at.title[0].value.endswith("Strateji karşılaştırma")
    assert len(at.tabs) == 2


def test_live_run_produces_report(at):
    at.number_input[0].set_value(20)
    at.button[0].click().run()  # formun "Çalıştır" düğmesi
    assert not at.exception
    report = at.session_state["okey_live_report"]
    assert report["n_games"] == 20
    assert [s["name"] for s in report["summaries"]] == ["Rastgele", "Açgözlü"]
    assert any("Son çalıştırma" in m.value for m in at.markdown)


def test_stored_reports_render_if_present(at):
    reports = sorted((ROOT / "docs" / "benchmarks").glob("*.json"))
    if not reports:
        assert any("bulunamadı" in i.value for i in at.info)
        return
    assert at.selectbox(key="saved_report").value.startswith("main_")
    assert len(at.dataframe) >= 1
