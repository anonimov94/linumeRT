#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Kompletność tłumaczeń ekranu (sesja 007). Model-Author: Claude · 2026-10-24.

Wydobywa z `screens/linumert/*.py` wywołania `translate("kontekst", "tekst")`, `_translate(...)`
i `QCoreApplication.translate(...)` z dosłownymi argumentami (te formy czyta pylupdate5)
i sprawdza, że każde ma ukończone tłumaczenie w `screens/linumert/i18n/linumert_pl.ts`.
Kod wyjścia 1 = brakujące albo nieukończone tłumaczenia (lista na stderr).
"""

import ast
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "screens/linumert"
TS = SCREENS / "i18n/linumert_pl.ts"


def calls(path):
    """[(kontekst, tekst, linia)] z dosłownych wywołań translate w pliku."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name not in ("translate", "_translate"):
            continue
        ctx, text = node.args[:2]
        if all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in (ctx, text)):
            found.append((ctx.value, text.value, node.lineno))
    return found


def source_messages(root=SCREENS):
    messages = {}
    for path in sorted(root.glob("*.py")):
        for ctx, text, line in calls(path):
            messages.setdefault((ctx, text), f"{path.name}:{line}")
    return messages


def ts_status(path=TS):
    """{(kontekst, źródło): 'done' | 'unfinished' | 'vanished'}."""
    status = {}
    if not path.is_file():
        return status
    for context in ElementTree.parse(path).getroot().iter("context"):
        name = context.findtext("name", "")
        for message in context.iter("message"):
            node = message.find("translation")
            kind = node.get("type") if node is not None else "unfinished"
            done = node is not None and bool(node.text) and kind is None
            status[(name, message.findtext("source"))] = "done" if done else (kind or "unfinished")
    return status


def problems(root=SCREENS, ts=TS):
    status = ts_status(ts)
    out = []
    for key, where in source_messages(root).items():
        state = status.get(key)
        if state != "done":
            out.append(f"{where}: [{key[0]}] {key[1]!r} — {state or 'brak w .ts'}")
    return out


def main():
    found = problems()
    for line in found:
        print(line, file=sys.stderr)
    total = len(source_messages())
    print(f"i18n: {total} tekstów, nieprzetłumaczonych {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
