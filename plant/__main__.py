"""`python -m plant ...` z katalogu głównego repozytorium — skrót do `python -m linumert_plant`.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 013 (REQ-VD-03: `python -m plant drive clone <źródło> <nowe_id>`).
Działa bez instalacji pakietu: dokłada plant/server i core do sys.path.
"""

import importlib
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    for path in (root / "server", root.parent / "core"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return importlib.import_module("linumert_plant.__main__").main()


if __name__ == "__main__":
    sys.exit(main())
