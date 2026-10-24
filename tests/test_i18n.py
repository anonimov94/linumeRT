# SPDX-License-Identifier: GPL-2.0-or-later
"""Sesja 007: tłumaczenia Qt ekranu — kompletność PL, tłumacz `.ts`, wybór języka.

Model-Author: Claude
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt5")
from PyQt5 import QtWidgets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "screens" / "linumert"))
import linumert_i18n as i18n  # noqa: E402

spec = importlib.util.spec_from_file_location("i18n_check", ROOT / "tools/i18n_check.py")
i18n_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i18n_check)


@pytest.fixture
def app():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app
    i18n.install("en", app)


def test_polish_translation_is_complete():
    assert i18n_check.problems() == []
    assert len(i18n_check.source_messages()) >= 2


def test_check_reports_missing_and_unfinished(tmp_path):
    (tmp_path / "view.py").write_text(
        'from linumert_i18n import translate\n'
        'a = translate("View", "Start")\n'
        'b = translate("View", "Stop")\n'
        'c = translate("View", name)\n', encoding="utf-8")
    ts = tmp_path / "pl.ts"
    ts.write_text('<?xml version="1.0"?><TS version="2.1"><context><name>View</name>'
                  '<message><source>Start</source><translation>Start</translation></message>'
                  '<message><source>Stop</source><translation type="unfinished"></translation>'
                  '</message></context></TS>', encoding="utf-8")
    found = i18n_check.problems(tmp_path, ts)
    assert len(found) == 1 and "'Stop'" in found[0] and "unfinished" in found[0]


def test_ts_translator_switches_language_without_lrelease(app, tmp_path, monkeypatch):
    monkeypatch.setattr(i18n, "I18N_DIR", ROOT / "screens/linumert/i18n")
    text = "Once: clear resolved alarms. Twice: also acknowledge E-STOP."
    translator = i18n.install("pl", app)
    assert translator is not None
    assert i18n.translate("AlarmPanel", text).startswith("Raz: skasuj")
    assert i18n.translate("AlarmPanel", "Untranslated") == "Untranslated"
    assert i18n.install("en", app) is None
    assert i18n.translate("AlarmPanel", text) == text
    with pytest.raises(ValueError):
        i18n.install("de", app)


def test_alarm_panel_uses_operator_language(app):
    from linumert_alarm_panel import AlarmPanel

    i18n.install("pl", app)
    panel = AlarmPanel(SimpleNamespace(reset_alarms=lambda both: None))
    assert panel.reset.toolTip().startswith("Raz: skasuj ustąpione alarmy")
    i18n.install("en", app)
    panel = AlarmPanel(SimpleNamespace(reset_alarms=lambda both: None))
    assert panel.reset.toolTip().startswith("Once: clear resolved alarms")


def test_language_from_env_ini_and_default(tmp_path, monkeypatch):
    ini = tmp_path / "m.ini"
    ini.write_text("[DISPLAY]\nLANGUAGE = de\n[LINUMERT]\nLANGUAGE = EN # komentarz\n")
    monkeypatch.delenv("LINUMERT_LANG", raising=False)
    assert i18n.language_from_ini(ini) == "en"
    assert i18n.language_from_ini(tmp_path / "brak.ini") == "pl"
    assert i18n.language_from_ini("") == "pl"
    monkeypatch.setenv("LINUMERT_LANG", "pl")
    assert i18n.language_from_ini(ini) == "pl"


@pytest.mark.skipif(shutil.which("pylupdate5") is None, reason="brak pylupdate5")
def test_pylupdate_extracts_the_same_messages(tmp_path):
    ts = tmp_path / "out.ts"
    sources = [str(p) for p in sorted((ROOT / "screens/linumert").glob("*.py"))
               if "translate(" in p.read_text(encoding="utf-8")]
    subprocess.run(["pylupdate5", "-noobsolete", *sources, "-ts", str(ts)], check=True,
                   capture_output=True)
    extracted = set(i18n_check.ts_status(ts))
    assert set(i18n_check.source_messages()) <= extracted
