#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""QSS powłoki linumeRT z docs/design/tokens.yaml (sesja 027). Model-Author: Claude · 2026-10-24.

Źródłem stylu jest `linumert_shell_model.shell_qss(tokens)`, wywoływane przez ekran w czasie
działania; ten skrypt zapisuje ten sam wynik do przeglądu albo porównania:
    python3 tools/gen_qss.py                 # na stdout
    python3 tools/gen_qss.py -o build/linumert-shell.qss
`screens/linumert/linumert.qss` to arkusz bazy QtDragon i nie jest nadpisywany.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "screens/linumert"))
import linumert_shell_model as model  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--output", help="plik wynikowy (domyślnie stdout)")
    parser.add_argument("--tokens", default=str(ROOT / "docs/design/tokens.yaml"))
    args = parser.parse_args(argv)
    qss = model.shell_qss(model.load_tokens(args.tokens))
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(qss, encoding="utf-8")
    else:
        sys.stdout.write(qss)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
