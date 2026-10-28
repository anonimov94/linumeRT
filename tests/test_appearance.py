# SPDX-License-Identifier: GPL-2.0-or-later
"""Wygląd HMI: palety, kontrola czytelności, zapis ustawień i strona Qt. Model-Author: Claude."""

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_APP = None
sys.path.insert(0, str(ROOT / "screens/linumert"))

import linumert_appearance as ap  # noqa: E402
import linumert_shell_model as model  # noqa: E402


# M2 (028): kolorystyka zmieniana w działającym HMI, z kontrolą czytelności
@pytest.mark.parametrize("preset", sorted(ap.PRESETS))
def test_every_preset_is_readable_and_maps_to_all_shell_tokens(preset):
    colors = ap.PRESETS[preset][1]
    assert ap.check(colors) == [], ap.check(colors)
    tokens = ap.apply_to_tokens(model.load_tokens(), colors)
    base = model.load_tokens()["kolory"]
    assert set(base) <= set(tokens["kolory"])               # żaden token nie znika
    assert tokens["rozmiary"] == model.load_tokens()["rozmiary"]
    assert tokens["kolory"]["bg"] == colors["background"]
    assert tokens["kolory"]["err"] == colors["error"]


def test_default_preset_reproduces_current_tokens_for_core_roles():
    base = model.load_tokens()["kolory"]
    tokens = ap.apply_to_tokens(model.load_tokens(), ap.default_colors())["kolory"]
    for key in ("bg", "panel", "raise", "fg", "fg2", "teal", "amber", "err", "ok", "info"):
        assert tokens[key] == base[key]


@pytest.mark.parametrize(("role", "value", "fragment"), [
    ("text", "#202830", "Tekst: kontrast"),                 # tekst nieczytelny na tle
    ("background", "#12171d", "nie do odróżnienia"),        # tło = panel
    ("error", "#2dd4bf", "czerwony"),                       # błąd w kolorze akcentu
    ("success", "#f87171", "zielony"),
    ("warning", "#4ade80", "bursztynowe"),
    ("accent", "zielony", "oczekiwano"),
    ("muted", "#101418", "Tekst pomocniczy"),
])
def test_unreadable_or_meaningless_colors_are_refused(role, value, fragment):
    colors = ap.default_colors()
    colors[role] = value
    problems = ap.check(colors)
    assert any(fragment in p for p in problems), problems
    with pytest.raises(ap.AppearanceError):
        ap.apply_to_tokens(model.load_tokens(), colors)


def test_contrast_is_wcag():
    assert ap.contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert ap.contrast("#777777", "#777777") == pytest.approx(1.0)


def test_save_load_reset_roundtrip(tmp_path):
    path = tmp_path / "appearance.json"
    assert ap.load(path)["preset"] == ap.DEFAULT_PRESET and ap.load(path)["note"] == ""
    colors = dict(ap.PRESETS["ion-blue"][1], accent="#ff8800")
    ap.save("custom", colors, path)
    loaded = ap.load(path)
    assert loaded["preset"] == "custom" and loaded["colors"]["accent"] == "#ff8800"
    assert not list(tmp_path.glob("*.tmp"))
    with pytest.raises(ap.AppearanceError):
        ap.save("custom", dict(colors, text="#101010"), path)           # nie nadpisuje poprawnego
    assert ap.load(path)["colors"]["accent"] == "#ff8800"
    ap.reset(path)
    assert not path.exists() and ap.load(path)["preset"] == ap.DEFAULT_PRESET


@pytest.mark.parametrize("content", ["nie json", "[]", json.dumps({"version": 9}),
                                     json.dumps({"version": 1, "colors": {"text": "#fff"}}),
                                     json.dumps({"version": 1, "preset": "custom",
                                                 "colors": {**ap.default_colors(),
                                                            "text": "#0a0c10"}})])
def test_corrupt_or_unsafe_file_falls_back_to_default(tmp_path, content):
    path = tmp_path / "a.json"
    path.write_text(content, encoding="utf-8")
    loaded = ap.load(path)
    assert loaded["preset"] == ap.DEFAULT_PRESET and loaded["colors"] == ap.default_colors()
    assert loaded["note"]


def test_environment_variable_selects_the_settings_file(tmp_path, monkeypatch):
    monkeypatch.setenv("LINUMERT_APPEARANCE", str(tmp_path / "x.json"))
    assert ap.settings_path() == tmp_path / "x.json"


# ---- strona Qt (offscreen, bez LinuxCNC) ---------------------------------------------------------
def _page(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt5")
    from linumert_appearance_page import AppearancePage
    from PyQt5 import QtWidgets

    global _APP
    _APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    class Shell:
        tokens = model.load_tokens()
        applied: list = []

        def apply_tokens(self, tokens):
            self.applied.append(tokens)
            self.tokens = tokens

    shell = Shell()
    shell.applied = []
    return AppearancePage(shell, tmp_path / "a.json"), shell


def test_page_preset_edit_save_and_reset(tmp_path):
    page, shell = _page(tmp_path)
    page.preset_buttons["neon-punk"].click()
    assert shell.applied[-1]["kolory"]["teal"] == "#00f0ff" and page.preset == "neon-punk"
    page.edits["accent"].setText("#ff8800")
    page.edits["accent"].editingFinished.emit()
    assert page.preset == "custom" and page.colors["accent"] == "#ff8800"
    page.btn_save.click()
    assert (tmp_path / "a.json").is_file() and "Zapisano" in page.status.text()
    assert shell.applied[-1]["kolory"]["teal"] == "#ff8800"
    page.btn_reset.click()
    assert not (tmp_path / "a.json").exists() and page.preset == ap.DEFAULT_PRESET
    assert shell.applied[-1]["kolory"]["teal"] == "#2dd4bf"


def test_page_blocks_unreadable_colors_and_bad_input(tmp_path):
    page, shell = _page(tmp_path)
    before = len(shell.applied)
    page.edits["text"].setText("#0b0d10")                 # prawie czarny tekst na czarnym tle
    page.edits["text"].editingFinished.emit()
    assert not page.btn_apply.isEnabled() and not page.btn_save.isEnabled()
    assert "kontrast" in page.status.text()
    page.btn_save.click()                                 # zablokowane: nic nie zapisano
    assert not (tmp_path / "a.json").exists() and len(shell.applied) == before
    page.edits["error"].setText("nie-kolor")
    page.edits["error"].editingFinished.emit()
    assert page.colors["error"] == ap.default_colors()["error"]
    assert "oczekiwano" in page.status.text()
