#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Monitor postępu HMI: odświeżana lista w terminalu. Model-Author: Codex.

Uruchom: python3 tools/dev/hmi-progress.py
Aktualizacja: python3 tools/dev/hmi-progress.py --done 1 --active 2 --once
"""

import argparse
import json
import sys
import time
from pathlib import Path

STEPS = (
    "Geometria: prostopadłościan, walec, rura, odlew",
    "Profil odlewu: punkty konturu i obrót 360°",
    "Widok Zero detalu: maszyna i przygotówka",
    "Edycja wymiarów, konturu i położenia",
    "Zapis przygotówki i ustawienie G54–G59",
    "Testy, commit i push",
)
STATE = Path(__file__).resolve().parents[2] / "state/hmi-zero-progress.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--done", type=int, choices=range(1, 7), action="append", default=[])
    parser.add_argument("--active", type=int, choices=range(1, 7))
    parser.add_argument("--note")
    args = parser.parse_args()
    if args.done or args.active or args.note:
        state = json.loads(STATE.read_text()) if STATE.exists() else {"done": [], "active": 1}
        state["done"] = sorted(set(state["done"]) | set(args.done))
        if args.active:
            state["active"] = args.active
        if args.note:
            state["note"] = args.note
        STATE.parent.mkdir(parents=True, exist_ok=True)
        temporary = STATE.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        temporary.replace(STATE)
    try:
        while True:
            state = json.loads(STATE.read_text()) if STATE.exists() else {"done": [], "active": 1}
            rows = ["linumeRT — ZERO DETALU", ""]
            for index, title in enumerate(STEPS, 1):
                mark = "✓" if index in state["done"] else "▶" if state["active"] == index else " "
                rows.append(f"[{mark}] {index}. {title}")
            rows += ["", state.get("note", ""), "",
                     f"Gotowe: {len(state['done'])}/6 · Ctrl+C zamyka monitor"]
            clear = "\033[2J\033[H" if sys.stdout.isatty() else ""
            print(clear + "\n".join(rows), flush=True)
            if args.once or not sys.stdout.isatty():
                return
            time.sleep(1)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
