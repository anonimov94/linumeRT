"""Zarządzanie PIN-ami ról ekranu (sesja 036). Model-Author: Claude · 2026-10-24.

    python -m linumert.access set-pin  --db <plik.sqlite> --role serwis|technolog
    python -m linumert.access clear-pin --db <plik.sqlite> --role technolog
    python -m linumert.access audit    --db <plik.sqlite> [--limit 50]

PIN podaje się interaktywnie (bez echa, dwa razy); nie trafia do historii powłoki.
Domyślna baza ekranu: katalog konfiguracji maszyny, `[LINUMERT]ACCESS_DB` w INI.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import argparse
import getpass
import sys
import time

from . import ROLES, AccessError, AccessStore


def main(argv=None, ask=getpass.getpass) -> int:
    parser = argparse.ArgumentParser(prog="python -m linumert.access", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("set-pin", "clear-pin"):
        p = sub.add_parser(name)
        p.add_argument("--db", required=True)
        p.add_argument("--role", required=True, choices=ROLES[1:])
    p = sub.add_parser("audit")
    p.add_argument("--db", required=True)
    p.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    store = AccessStore(args.db)
    try:
        if args.cmd == "set-pin":
            pin = ask(f"Nowy PIN dla roli {args.role}: ")
            if pin != ask("Powtórz PIN: "):
                print("PIN-y różnią się; nic nie zmieniono.", file=sys.stderr)
                return 1
            store.set_pin(args.role, pin, by="cli")
            print(f"Ustawiono PIN roli {args.role}. Kontrola dostępu jest włączona.")
        elif args.cmd == "clear-pin":
            store.clear_pin(args.role, by="cli")
            left = sorted(store.configured_roles())
            print(f"Usunięto PIN roli {args.role}." + ("" if left else
                  " Brak PIN-ów: kontrola dostępu wyłączona."))
        else:
            for ts, role, action, detail in store.history(args.limit):
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}  "
                      f"{role:<9} {action:<13} {detail}")
    except AccessError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
