# SPDX-License-Identifier: GPL-2.0-or-later
"""Sesja 027: QSS z tokenów (gen_qss), fonty OFL dołączone do ekranu i ich pochodzenie.

Model-Author: Claude
"""

import hashlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "screens/linumert/fonts"
sys.path.insert(0, str(ROOT / "screens/linumert"))


def _gen_qss():
    spec = importlib.util.spec_from_file_location("gen_qss", ROOT / "tools/gen_qss.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gen_qss_writes_runtime_style_from_tokens(tmp_path):
    import linumert_shell_model as model

    out = tmp_path / "shell.qss"
    assert _gen_qss().main(["-o", str(out)]) == 0
    qss = out.read_text(encoding="utf-8")
    tokens = yaml.safe_load((ROOT / "docs/design/tokens.yaml").read_text(encoding="utf-8"))
    assert qss == model.shell_qss(model.load_tokens())
    assert f"min-height: {tokens['rozmiary']['cel_dotykowy_px']}px" in qss
    assert tokens["rozmiary"]["cel_dotykowy_px"] >= 44 and tokens["rozmiary"]["dro_px"] >= 28
    assert tokens["rozmiary"]["odstep_px"] == 8


def test_font_files_have_license_and_provenance():
    provenance = (ROOT / "docs/PROVENANCE.md").read_text(encoding="utf-8")
    licences = (ROOT / "docs/LICENCJE.md").read_text(encoding="utf-8")
    ttfs = sorted(FONTS.glob("*.ttf"))
    assert {p.name.split("-")[0] for p in ttfs} == {"IBMPlexSans", "JetBrainsMono"}
    for family in ("IBMPlexSans", "JetBrainsMono"):
        text = (FONTS / f"OFL-{family}.txt").read_text(encoding="utf-8")
        assert "SIL Open Font License" in text and "Version 1.1" in text
    for path in ttfs:
        assert path.read_bytes()[:4] in (b"\x00\x01\x00\x00", b"true")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert f"`screens/linumert/fonts/{path.name}`" in provenance, path.name
        assert digest in provenance, path.name
    assert "IBM Plex Sans" in licences and "JetBrains Mono" in licences


def test_fonts_register_in_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt5")
    from PyQt5 import QtGui, QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841
    from linumert_fonts import FAMILIES, register

    families, missing = register()
    assert not missing
    assert set(FAMILIES) <= set(families)
    assert set(FAMILIES) <= set(QtGui.QFontDatabase().families())
    assert register()[0] == families              # drugi raz bez ponownej rejestracji
