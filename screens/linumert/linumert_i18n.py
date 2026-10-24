# SPDX-License-Identifier: GPL-2.0-or-later
"""Tłumaczenia Qt ekranu linumeRT (sesja 007): `.qm` z lrelease albo `.ts` wprost.

Model-Author: Claude · 2026-10-24.

Zasada: każdy nowy tekst widoczny dla operatora przechodzi przez `translate(kontekst, tekst)`
(`QCoreApplication.translate`; tę formę rozpoznaje pylupdate5 — `tr(kontekst, tekst)` nie),
z tekstem źródłowym po angielsku (docelowy język domyślny
skórek, SKIN_SYSTEM_ROADMAP). Tłumaczenia leżą w `screens/linumert/i18n/linumert_<język>.ts`
i są aktualizowane przez `tools/i18n.sh` (pylupdate5). Jeśli obok jest `.qm` z `lrelease`,
ładowany jest on; w przeciwnym razie `TsTranslator` czyta `.ts` bezpośrednio — ekran działa
bez kroku budowania, a `lrelease` jest tylko przyspieszeniem startu.
"""

from pathlib import Path
from xml.etree import ElementTree

from PyQt5 import QtCore

I18N_DIR = Path(__file__).with_name("i18n")
LANGUAGES = ("en", "pl")
SOURCE_LANGUAGE = "en"

_installed = []


def translate(context, text):
    """Tekst operatora w bieżącym języku (bez tłumaczenia = tekst źródłowy)."""
    return QtCore.QCoreApplication.translate(context, text)


def read_ts(path):
    """{(kontekst, źródło): tłumaczenie} z ukończonych wpisów pliku `.ts`."""
    table = {}
    root = ElementTree.parse(path).getroot()
    for context in root.iter("context"):
        name = context.findtext("name", "")
        for message in context.iter("message"):
            source = message.findtext("source")
            node = message.find("translation")
            if source is None or node is None:
                continue
            if node.get("type") in ("unfinished", "vanished", "obsolete") or not node.text:
                continue
            table[(name, source)] = node.text
    return table


class TsTranslator(QtCore.QTranslator):
    """QTranslator czytający `.ts` bez lrelease (tylko ukończone tłumaczenia)."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.table = read_ts(path)

    def translate(self, context, source, disambiguation=None, n=-1):
        # None = null QString = „brak tłumaczenia” (Qt pokaże źródło); "" dałoby pusty napis.
        return self.table.get((context, source))

    def isEmpty(self):
        return not self.table


def language_from_ini(path, default="pl"):
    """Język ekranu: `LINUMERT_LANG`, potem `[LINUMERT]LANGUAGE` z INI, potem `default`."""
    import os
    env = os.environ.get("LINUMERT_LANG", "").strip().lower()
    if env in LANGUAGES:
        return env
    section = ""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.split("#", 1)[0].strip()
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].strip().upper()
                elif section == "LINUMERT" and "=" in line:
                    key, value = (part.strip() for part in line.split("=", 1))
                    if key.upper() == "LANGUAGE" and value.lower() in LANGUAGES:
                        return value.lower()
    except (OSError, TypeError):
        pass
    return default


def install(language, app=None):
    """Włącza język ekranu; poprzedni tłumacz linumeRT jest usuwany. Zwraca tłumacza albo None."""
    if language not in LANGUAGES:
        raise ValueError(f"Nieobsługiwany język: {language!r}")
    app = app or QtCore.QCoreApplication.instance()
    while _installed:
        app.removeTranslator(_installed.pop())
    if language == SOURCE_LANGUAGE:
        return None
    qm = I18N_DIR / f"linumert_{language}.qm"
    ts = I18N_DIR / f"linumert_{language}.ts"
    translator = QtCore.QTranslator(app)
    if not (qm.is_file() and translator.load(str(qm))):
        translator = TsTranslator(ts, app)
    app.installTranslator(translator)
    _installed.append(translator)
    return translator
