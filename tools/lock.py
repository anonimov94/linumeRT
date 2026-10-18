#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Blokady zasobów współdzielonych (np. `linuxcnc`, `wsl-build`) dla Claude i Codexa.

Model-Author: Claude · D30. Blokada to plik `state/locks/<zasób>.lock` (katalog ignorowany
przez Git, nadpisywany zmienną `LINUMERT_LOCK_DIR`). Tworzenie jest atomowe (O_EXCL). Blokada
starsza niż TTL (domyślnie 2 h, jak w docs/WSPOLPRACA_MODELI.md §1) jest uznawana za przerwaną.

    python tools/lock.py acquire linuxcnc --model Codex --note "sesja 018, RIP"
    python tools/lock.py status
    python tools/lock.py release linuxcnc --model Codex

Kody wyjścia: 0 sukces, 1 zasób zajęty, 2 błąd użycia.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

DEFAULT_TTL = 2 * 3600
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def lock_dir() -> Path:
    env = os.environ.get("LINUMERT_LOCK_DIR")
    return Path(env) if env else Path(__file__).resolve().parent.parent / "state" / "locks"


def _path(resource: str) -> Path:
    if not NAME_RE.match(resource):
        raise ValueError(f"niepoprawna nazwa zasobu: {resource!r} (małe litery, cyfry, - i _)")
    return lock_dir() / f"{resource}.lock"


def read(resource: str) -> dict | None:
    try:
        return json.loads(_path(resource).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"model": "?", "ts": 0.0, "ttl": 0, "note": "uszkodzony plik blokady"}


def expired(info: dict, now: float) -> bool:
    return now > float(info.get("ts", 0)) + float(info.get("ttl", DEFAULT_TTL))


def acquire(resource: str, model: str, note: str = "", ttl: int = DEFAULT_TTL,
            now: float | None = None) -> tuple[bool, dict | None]:
    """Zwraca (True, poprzedni_przerwany_właściciel|None) albo (False, aktualny_właściciel)."""
    now = time.time() if now is None else now
    path = _path(resource)
    path.parent.mkdir(parents=True, exist_ok=True)
    takeover = None
    current = read(resource)
    if current is not None:
        if current.get("model") == model:
            takeover = None  # własna blokada: odświeżenie
        elif not expired(current, now):
            return False, current
        else:
            takeover = current
        path.unlink(missing_ok=True)
    info = {"model": model, "ts": now, "ttl": ttl, "note": note, "pid": os.getpid()}
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False, read(resource)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False)
    return True, takeover


def release(resource: str, model: str, force: bool = False) -> bool:
    current = read(resource)
    if current is None:
        return True
    if current.get("model") != model and not force:
        return False
    _path(resource).unlink(missing_ok=True)
    return True


def _fmt(resource: str, info: dict, now: float) -> str:
    age = int((now - float(info.get("ts", 0))) / 60)
    state = "PRZERWANA (>TTL)" if expired(info, now) else "aktywna"
    return f"{resource}: {info.get('model')} · {age} min temu · {state} · {info.get('note', '')}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("acquire", "release"):
        p = sub.add_parser(name)
        p.add_argument("resource")
        p.add_argument("--model", required=True, choices=["Claude", "Codex"])
        if name == "acquire":
            p.add_argument("--note", default="")
            p.add_argument("--ttl", type=int, default=DEFAULT_TTL)
        else:
            p.add_argument("--force", action="store_true")
    st = sub.add_parser("status")
    st.add_argument("resource", nargs="?")
    a = ap.parse_args(argv)
    try:
        now = time.time()
        if a.cmd == "status":
            names = [a.resource] if a.resource else sorted(
                p.stem for p in lock_dir().glob("*.lock")) if lock_dir().exists() else []
            for r in names:
                info = read(r)
                print(_fmt(r, info, now) if info else f"{r}: wolny")
            if not names:
                print("brak blokad")
            return 0
        if a.cmd == "acquire":
            ok, other = acquire(a.resource, a.model, a.note, a.ttl, now)
            if not ok:
                print("ZAJĘTE: " + _fmt(a.resource, other or {}, now), file=sys.stderr)
                return 1
            if other:
                print("przejęto przerwaną blokadę: " + _fmt(a.resource, other, now))
            print(f"{a.resource}: zablokowany przez {a.model}")
            return 0
        if not release(a.resource, a.model, a.force):
            print("nie twoja blokada (użyj --force tylko dla przerwanej)", file=sys.stderr)
            return 1
        print(f"{a.resource}: zwolniony")
        return 0
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
